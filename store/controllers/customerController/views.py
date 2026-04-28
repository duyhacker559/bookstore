import json
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q, Max, OuterRef, Subquery, Prefetch, prefetch_related_objects
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.urls import reverse
from django.conf import settings
from datetime import datetime
from store.models.customer.customer import Customer
from store.models.order.order import Order
from store.models.order.order_item import OrderItem
from store.models.user_profile import UserProfile
from store.models.product.product import Book
from store.models.rating.rating import Comment
from store.models.communication import (
    UserNotification,
    InboxMessage,
    InboxReply,
    AIChatSession,
    AIChatMessage,
)
from store.services.notification_service import create_user_notification
from store.behavior_client import BehaviorClient, BehaviorServiceError, BehaviorServiceUnavailable
from store.rag_client import RAGClient, RAGServiceError, RAGServiceUnavailable
from store.ai_behavior_client import AIBehaviorClient, AIBehaviorServiceError, AIBehaviorServiceUnavailable
from store.services.ai_behavior_tracking import (
    build_session_event_signals,
    get_recently_viewed_product_ids,
    infer_preferred_category_from_events,
)
from decimal import Decimal


MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 2MB
ALLOWED_AVATAR_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


def _use_advanced_ai_widget() -> bool:
    return bool(getattr(settings, 'AI_ADVANCED_WIDGET_ENABLED', False))


def _push_advanced_behavior_events(
    advanced_client,
    customer_id,
    session_id,
    session_events,
    viewed_product_ids,
    question='',
):
    events = []

    for raw_event in session_events[-20:]:
        event_type = str(raw_event or '').strip()
        if not event_type:
            continue
        events.append(
            {
                'user_id': int(customer_id),
                'session_id': session_id,
                'event_type': event_type,
                'metadata': {'surface': 'web_widget'},
            }
        )

    for product_id in viewed_product_ids[:10]:
        try:
            normalized_id = int(product_id)
        except (TypeError, ValueError):
            continue
        events.append(
            {
                'user_id': int(customer_id),
                'session_id': session_id,
                'event_type': 'product_detail_view',
                'product_id': normalized_id,
                'metadata': {'surface': 'web_widget'},
            }
        )

    if question:
        events.append(
            {
                'user_id': int(customer_id),
                'session_id': session_id,
                'event_type': 'chat_question',
                'query_text': str(question),
                'metadata': {'surface': 'web_widget'},
            }
        )

    if not events:
        return

    try:
        advanced_client.ingest_batch(events)
    except (AIBehaviorServiceUnavailable, AIBehaviorServiceError):
        # Do not fail user-facing flow when telemetry ingestion fails.
        return


def _serialize_recommended_products(product_ids):
    normalized_ids = []
    for raw_id in product_ids or []:
        try:
            normalized = int(raw_id)
        except (TypeError, ValueError):
            continue
        if normalized not in normalized_ids:
            normalized_ids.append(normalized)

    if not normalized_ids:
        return []

    products = Book.objects.filter(id__in=normalized_ids).only(
        'id', 'title', 'price', 'product_type', 'stock'
    )
    product_map = {product.id: product for product in products}

    result = []
    for product_id in normalized_ids:
        product = product_map.get(product_id)
        if not product:
            continue
        result.append(
            {
                'id': product.id,
                'title': product.title,
                'price': float(product.price),
                'product_type': product.product_type,
                'stock': product.stock,
                'detail_url': reverse(
                    'detail',
                    kwargs={'product_type': product.product_type, 'book_id': product.id},
                ),
            }
        )

    return result


def _tokenize_text(text):
    return [token for token in re.split(r'[^a-z0-9]+', (text or '').lower()) if token]


def _infer_preferred_category(customer):
    ordered_types = (
        OrderItem.objects.filter(order__customer=customer)
        .values('book__product_type')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    for item in ordered_types:
        value = (item.get('book__product_type') or '').strip().lower()
        if value:
            return value
    return ''


def _build_catalog_hints(question, top_k=30):
    tokens = _tokenize_text(question)
    queryset = Book.objects.filter(stock__gt=0).only('id', 'title', 'price', 'product_type', 'stock')

    if tokens:
        query = Q()
        for token in tokens[:8]:
            query |= Q(title__icontains=token) | Q(product_type__icontains=token)
        matched_qs = queryset.filter(query).order_by('-id')[:top_k]
        if matched_qs:
            queryset = matched_qs
        else:
            queryset = queryset.order_by('-id')[:top_k]
    else:
        queryset = queryset.order_by('-id')[:top_k]

    return [
        {
            'id': product.id,
            'title': product.title,
            'category': product.product_type,
            'price': float(product.price),
            'stock': product.stock,
        }
        for product in queryset
    ]


def _catalog_hints_from_product_ids(product_ids, top_k=20):
    normalized_ids = []
    for raw_id in product_ids or []:
        try:
            product_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if product_id not in normalized_ids:
            normalized_ids.append(product_id)

    if not normalized_ids:
        return []

    products = Book.objects.filter(id__in=normalized_ids, stock__gt=0).only('id', 'title', 'price', 'product_type', 'stock')
    product_map = {product.id: product for product in products}

    result = []
    for product_id in normalized_ids[:top_k]:
        product = product_map.get(product_id)
        if not product:
            continue
        result.append(
            {
                'id': product.id,
                'title': product.title,
                'category': product.product_type,
                'price': float(product.price),
                'stock': product.stock,
            }
        )
    return result


def _merge_catalog_hints(primary_hints, secondary_hints, top_k=30):
    merged = []
    seen = set()

    for hint in (primary_hints or []) + (secondary_hints or []):
        if not isinstance(hint, dict):
            continue
        try:
            product_id = int(hint.get('id'))
        except (TypeError, ValueError):
            continue
        if product_id in seen:
            continue
        seen.add(product_id)
        merged.append(hint)
        if len(merged) >= top_k:
            break

    return merged


def _customer_inbox_activity_snapshot(customer):
    inbox_qs = InboxMessage.objects.filter(customer=customer)
    unread_count = inbox_qs.filter(status='unread').count()
    latest_reply = InboxReply.objects.filter(inbox_message__customer=customer).aggregate(last=Max('created_at'))['last']
    latest_message = inbox_qs.aggregate(last=Max('created_at'))['last']
    latest_candidates = [dt for dt in [latest_reply, latest_message] if dt is not None]
    latest_activity = max(latest_candidates) if latest_candidates else None
    latest_token = latest_activity.isoformat() if latest_activity else ''
    return unread_count, latest_token


def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            Customer.objects.create(user=user, name=user.username, email=user.email)
            login(request, user)
            return redirect("/")
    else:
        form = UserCreationForm()
    return render(request, "customer/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("/")
    else:
        form = AuthenticationForm()
    return render(request, "customer/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("/")


@login_required(login_url='login')
def customer_home(request):
    """Display customer dashboard with real user data."""
    customer = get_object_or_404(Customer, user=request.user)
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)

    orders = Order.objects.filter(customer=customer).order_by('-created_at')
    reviewed_books = (
        Comment.objects.filter(customer=customer)
        .select_related('book', 'rating')
        .order_by('-created_at')[:8]
    )
    total_orders = orders.count()
    total_books = OrderItem.objects.filter(order__customer=customer).aggregate(total=Sum('quantity'))['total'] or 0
    total_spent = orders.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    delivered_orders = orders.filter(status__iexact='Delivered').count()

    checklist = [
        {'label': 'Full Name',       'done': bool((customer.name or '').strip()),         'tab': 'profile'},
        {'label': 'Email Address',   'done': bool((customer.email or '').strip()),        'tab': 'profile'},
        {'label': 'Phone Number',    'done': bool((customer.phone or '').strip()),        'tab': 'profile'},
        {'label': 'Delivery Address','done': bool((customer.address or '').strip()),     'tab': 'profile'},
        {'label': 'Profile Photo',   'done': bool(user_profile.avatar),                  'tab': 'profile'},
    ]
    completed_fields = sum(1 for item in checklist if item['done'])
    profile_completion = int((completed_fields / len(checklist)) * 100)

    order_id_query = request.GET.get('order_id', '').strip()
    status = request.GET.get('status')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    try:
        page_size = int(request.GET.get('page_size', 10))
    except (TypeError, ValueError):
        page_size = 10
    page_size = max(1, min(page_size, 50))

    if order_id_query:
        try:
            orders = orders.filter(id=int(order_id_query))
        except ValueError:
            orders = orders.none()

    if status:
        orders = orders.filter(status__iexact=status)

    if start_date:
        try:
            sd = datetime.strptime(start_date, '%Y-%m-%d')
            orders = orders.filter(created_at__date__gte=sd.date())
        except ValueError:
            pass
    if end_date:
        try:
            ed = datetime.strptime(end_date, '%Y-%m-%d')
            orders = orders.filter(created_at__date__lte=ed.date())
        except ValueError:
            pass

    page = request.GET.get('page', 1)
    paginator = Paginator(orders, page_size)
    try:
        orders_page = paginator.page(page)
    except PageNotAnInteger:
        orders_page = paginator.page(1)
    except EmptyPage:
        orders_page = paginator.page(paginator.num_pages)

    base_qs = request.GET.copy()
    if 'page' in base_qs:
        del base_qs['page']
    base_query = base_qs.urlencode()

    context = {
        'customer': customer,
        'user_profile': user_profile,
        'total_orders': total_orders,
        'total_books': total_books,
        'total_spent': total_spent,
        'delivered_orders': delivered_orders,
        'profile_completion': profile_completion,
        'checklist': checklist,
        'orders_page': orders_page,
        'reviewed_books': reviewed_books,
        'base_query': base_query,
        'filters': {
            'status': status or '',
            'start_date': start_date or '',
            'end_date': end_date or '',
            'page_size': page_size,
            'order_id': order_id_query,
        }
    }
    return render(request, "customer/home.html", context)


@login_required(login_url='login')
def notifications(request):
    customer, _ = Customer.objects.get_or_create(
        user=request.user,
        defaults={'name': request.user.username, 'email': request.user.email}
    )
    notifications_qs = UserNotification.objects.filter(customer=customer).order_by('-created_at')
    paginator = Paginator(notifications_qs, 20)
    page_number = request.GET.get('page', 1)
    notifications_page = paginator.get_page(page_number)
    return render(request, 'customer/notifications.html', {
        'notifications': notifications_page,
        'notifications_page': notifications_page,
    })


@login_required(login_url='login')
def notification_updates(request):
    customer = Customer.objects.filter(user=request.user).first()
    unread_count = 0
    inbox_available_count = 0
    if customer:
        counters = UserNotification.objects.filter(customer=customer).aggregate(
            unread_count=Count('id', filter=Q(is_read=False)),
            inbox_available_count=Count('id', filter=Q(is_read=False, link__startswith='/customer/inbox/')),
        )
        unread_count = counters.get('unread_count') or 0
        inbox_available_count = counters.get('inbox_available_count') or 0
    return JsonResponse({
        'unread_count': unread_count,
        'inbox_available_count': inbox_available_count,
    })


@login_required(login_url='login')
def mark_notification_read(request, notification_id):
    customer, _ = Customer.objects.get_or_create(
        user=request.user,
        defaults={'name': request.user.username, 'email': request.user.email}
    )
    notification = get_object_or_404(UserNotification, id=notification_id, customer=customer)
    if request.method == 'POST' and not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=['is_read', 'read_at'])
    return redirect('customer_notifications')


@login_required(login_url='login')
def mark_all_notifications_read(request):
    customer, _ = Customer.objects.get_or_create(
        user=request.user,
        defaults={'name': request.user.username, 'email': request.user.email}
    )
    if request.method == 'POST':
        UserNotification.objects.filter(customer=customer, is_read=False).update(
            is_read=True,
            read_at=timezone.now(),
        )
        messages.success(request, 'All notifications marked as read.')
    return redirect('customer_notifications')


@login_required(login_url='login')
def customer_inbox(request):
    customer, _ = Customer.objects.get_or_create(
        user=request.user,
        defaults={'name': request.user.username, 'email': request.user.email}
    )
    prefill_product = None
    thread_state = request.GET.get('thread_state', 'all').strip()
    book_id = request.GET.get('book_id', '').strip()
    if book_id:
        try:
            prefill_product = Book.objects.filter(id=int(book_id)).first()
        except ValueError:
            prefill_product = None

    if request.method == 'POST':
        action = request.POST.get('action', 'new_message').strip()

        if action == 'mark_as_read':
            message_id = request.POST.get('message_id', '').strip()
            inbox_message = get_object_or_404(InboxMessage, id=message_id, customer=customer)
            inbox_message.status = 'read'
            inbox_message.read_at = timezone.now()
            inbox_message.save(update_fields=['status', 'read_at'])
            UserNotification.objects.filter(
                customer=customer,
                link=f"/customer/inbox/{inbox_message.id}/",
                is_read=False,
            ).update(is_read=True, read_at=timezone.now())
            messages.success(request, 'Message marked as read.')
            return redirect('customer_inbox')

        if action == 'reply':
            message_id = request.POST.get('message_id', '').strip()
            reply_content = request.POST.get('reply_content', '').strip()
            inbox_message = get_object_or_404(InboxMessage, id=message_id, customer=customer)

            if not reply_content:
                messages.error(request, 'Reply message cannot be empty.')
                return redirect('customer_inbox')

            InboxReply.objects.create(
                inbox_message=inbox_message,
                sender_type='customer',
                content=reply_content,
            )
            inbox_message.status = 'unread'
            inbox_message.read_at = None
            inbox_message.save(update_fields=['status', 'read_at'])
            UserNotification.objects.filter(
                customer=customer,
                link=f"/customer/inbox/{inbox_message.id}/",
                is_read=False,
            ).update(is_read=True, read_at=timezone.now())
            messages.success(request, 'Your reply has been sent to staff.')
            return redirect('customer_inbox')

        subject = request.POST.get('subject', '').strip()
        content = request.POST.get('content', '').strip()
        selected_book = request.POST.get('book_id', '').strip()
        book = None
        if selected_book:
            try:
                book = Book.objects.filter(id=int(selected_book)).first()
            except ValueError:
                book = None

        if not subject or not content:
            messages.error(request, 'Subject and message are required.')
            return redirect('customer_inbox')

        inbox_message = InboxMessage.objects.create(
            customer=customer,
            book=book,
            subject=subject,
            content=content,
        )
        InboxReply.objects.create(
            inbox_message=inbox_message,
            sender_type='customer',
            content=content,
        )
        messages.success(request, 'Your message has been sent to staff.')
        return redirect('customer_inbox')

    last_reply_qs = InboxReply.objects.filter(inbox_message=OuterRef('pk')).order_by('-created_at')
    messages_qs = (
        InboxMessage.objects.filter(customer=customer)
        .select_related('book')
        .annotate(
            reply_count=Count('replies'),
            last_reply_sender=Subquery(last_reply_qs.values('sender_type')[:1]),
            last_reply_created_at=Subquery(last_reply_qs.values('created_at')[:1]),
        )
        .order_by('-created_at')
    )

    if thread_state == 'awaiting_staff':
        messages_qs = messages_qs.filter(last_reply_sender='customer')
    elif thread_state == 'awaiting_you':
        messages_qs = messages_qs.filter(last_reply_sender='staff')

    paginator = Paginator(messages_qs, 10)
    page_number = request.GET.get('page', 1)
    inbox_page = paginator.get_page(page_number)

    inbox_messages = list(inbox_page.object_list)
    prefetch_related_objects(
        inbox_messages,
        Prefetch('replies', queryset=InboxReply.objects.order_by('created_at')),
    )
    for message_item in inbox_messages:
        replies = list(message_item.replies.all())
        message_item.last_reply = replies[-1] if replies else None
        message_item.reply_count = message_item.reply_count or len(replies)

    inbox_page.object_list = inbox_messages
    inbox_unread_count, inbox_latest_activity = _customer_inbox_activity_snapshot(customer)

    return render(request, 'customer/inbox.html', {
        'inbox_messages': inbox_messages,
        'inbox_page': inbox_page,
        'prefill_product': prefill_product,
        'thread_state': thread_state,
        'inbox_unread_count': inbox_unread_count,
        'inbox_latest_activity': inbox_latest_activity,
    })


@login_required(login_url='login')
def customer_inbox_thread(request, message_id):
    customer, _ = Customer.objects.get_or_create(
        user=request.user,
        defaults={'name': request.user.username, 'email': request.user.email}
    )
    inbox_message = get_object_or_404(
        InboxMessage.objects.select_related('book').prefetch_related('replies'),
        id=message_id,
        customer=customer,
    )

    if request.method == 'POST':
        action = request.POST.get('action', 'reply').strip()
        if action == 'mark_as_read':
            inbox_message.status = 'read'
            inbox_message.read_at = timezone.now()
            inbox_message.save(update_fields=['status', 'read_at'])
            UserNotification.objects.filter(
                customer=customer,
                link=f"/customer/inbox/{inbox_message.id}/",
                is_read=False,
            ).update(is_read=True, read_at=timezone.now())
            messages.success(request, 'Message marked as read.')
            return redirect('customer_inbox_thread', message_id=inbox_message.id)

        reply_content = request.POST.get('reply_content', '').strip()
        if not reply_content:
            messages.error(request, 'Reply message cannot be empty.')
            return redirect('customer_inbox_thread', message_id=inbox_message.id)

        InboxReply.objects.create(
            inbox_message=inbox_message,
            sender_type='customer',
            content=reply_content,
        )
        inbox_message.status = 'unread'
        inbox_message.read_at = None
        inbox_message.save(update_fields=['status', 'read_at'])
        UserNotification.objects.filter(
            customer=customer,
            link=f"/customer/inbox/{inbox_message.id}/",
            is_read=False,
        ).update(is_read=True, read_at=timezone.now())
        messages.success(request, 'Your reply has been sent to staff.')
        return redirect('customer_inbox_thread', message_id=inbox_message.id)

    inbox_unread_count, inbox_latest_activity = _customer_inbox_activity_snapshot(customer)

    latest_thread_reply = inbox_message.replies.aggregate(last=Max('created_at'))['last']

    return render(request, 'customer/inbox_thread.html', {
        'inbox_message': inbox_message,
        'inbox_unread_count': inbox_unread_count,
        'inbox_latest_activity': inbox_latest_activity,
        'thread_latest_activity': latest_thread_reply.isoformat() if latest_thread_reply else '',
    })


@login_required(login_url='login')
def customer_inbox_updates(request):
    customer, _ = Customer.objects.get_or_create(
        user=request.user,
        defaults={'name': request.user.username, 'email': request.user.email}
    )
    unread_count, latest_token = _customer_inbox_activity_snapshot(customer)
    return JsonResponse({
        'unread_count': unread_count,
        'latest_activity': latest_token,
    })


@login_required(login_url='login')
def customer_inbox_thread_updates(request, message_id):
    customer, _ = Customer.objects.get_or_create(
        user=request.user,
        defaults={'name': request.user.username, 'email': request.user.email}
    )
    inbox_message = get_object_or_404(
        InboxMessage.objects.select_related('book').prefetch_related('replies'),
        id=message_id,
        customer=customer,
    )
    latest_thread_reply = inbox_message.replies.aggregate(last=Max('created_at'))['last']
    replies_html = render_to_string('customer/_inbox_replies.html', {
        'inbox_message': inbox_message,
    }, request=request)

    return JsonResponse({
        'latest_activity': latest_thread_reply.isoformat() if latest_thread_reply else '',
        'status': inbox_message.status,
        'replies_html': replies_html,
    })


@login_required(login_url='login')
def profile_settings(request):
    """Display profile settings page."""
    customer = get_object_or_404(Customer, user=request.user)
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return render(request, "customer/settings.html", {'customer': customer, 'user_profile': user_profile})


@login_required(login_url='login')
def update_profile(request):
    """Update customer profile information."""
    if request.method != 'POST':
        return redirect('customer_profile_settings')

    customer = get_object_or_404(Customer, user=request.user)
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)

    new_username = request.POST.get('username', '').strip()
    if new_username and new_username != request.user.username:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if User.objects.filter(username__iexact=new_username).exclude(pk=request.user.pk).exists():
            messages.error(request, 'That username is already taken. Please choose another.')
            return redirect('customer_profile_settings')
        if len(new_username) < 3:
            messages.error(request, 'Username must be at least 3 characters.')
            return redirect('customer_profile_settings')
        request.user.username = new_username
        request.user.save(update_fields=['username'])

    customer.name = request.POST.get('name', customer.name).strip()
    customer.email = request.POST.get('email', customer.email).strip()
    customer.phone = request.POST.get('phone', customer.phone or '').strip()
    customer.address = request.POST.get('address', customer.address or '').strip()

    new_email = customer.email
    if new_email and new_email != request.user.email:
        request.user.email = new_email
        request.user.save(update_fields=['email'])

    avatar_file = request.FILES.get('avatar')
    if avatar_file:
        if avatar_file.content_type not in ALLOWED_AVATAR_CONTENT_TYPES:
            messages.error(request, 'Invalid image type. Please upload JPG, PNG, WEBP, or GIF.')
            return redirect('customer_profile_settings')

        if avatar_file.size > MAX_AVATAR_SIZE:
            messages.error(request, 'Image is too large. Maximum size is 2MB.')
            return redirect('customer_profile_settings')

        user_profile.avatar = avatar_file
        user_profile.save(update_fields=['avatar'])

    customer.save()
    messages.success(request, 'Profile updated successfully!')
    return redirect('customer_profile_settings')


@login_required(login_url='login')
def remove_avatar(request):
    """Remove current user's avatar image."""
    if request.method != 'POST':
        return redirect('customer_profile_settings')

    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if user_profile.avatar:
        user_profile.avatar.delete(save=False)
        user_profile.avatar = None
        user_profile.save(update_fields=['avatar'])
        messages.success(request, 'Profile photo removed.')
    else:
        messages.info(request, 'No profile photo to remove.')

    return redirect('customer_profile_settings')


@login_required(login_url='login')
def change_password(request):
    """Change user password."""
    if request.method != 'POST':
        return redirect('customer_profile_settings')

    current_password = request.POST.get('current_password', '').strip()
    new_password = request.POST.get('new_password', '').strip()
    confirm_password = request.POST.get('confirm_password', '').strip()

    if not request.user.check_password(current_password):
        messages.error(request, 'Current password is incorrect')
        return redirect('customer_profile_settings')

    if new_password != confirm_password:
        messages.error(request, 'New passwords do not match')
        return redirect('customer_profile_settings')

    if len(new_password) < 8:
        messages.error(request, 'Password must be at least 8 characters long')
        return redirect('customer_profile_settings')

    request.user.set_password(new_password)
    request.user.save()
    update_session_auth_hash(request, request.user)

    messages.success(request, 'Password changed successfully!')
    return redirect('customer_profile_settings')


@login_required(login_url='login')
@require_POST
def ai_chat_widget(request):
    customer, _ = Customer.objects.get_or_create(
        user=request.user,
        defaults={'name': request.user.username, 'email': request.user.email}
    )

    try:
        payload = json.loads(request.body.decode('utf-8')) if request.body else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'Invalid JSON payload'}, status=400)

    question = (payload.get('question') or '').strip()
    if not question:
        return JsonResponse({'error': 'Missing question'}, status=400)

    session_id = (payload.get('session_id') or f'web-user-{request.user.id}')[:120]
    context = payload.get('context') if isinstance(payload.get('context'), dict) else {}
    context = dict(context)

    session_events = build_session_event_signals(request, limit=30)
    viewed_product_ids = get_recently_viewed_product_ids(request, limit=12)
    viewed_hints = _catalog_hints_from_product_ids(viewed_product_ids)
    query_hints = _build_catalog_hints(question)
    catalog_hints = _merge_catalog_hints(viewed_hints, query_hints, top_k=30)

    if 'catalog_hints' not in context:
        context['catalog_hints'] = catalog_hints
    if 'session_events' not in context and session_events:
        context['session_events'] = session_events

    inferred_category = infer_preferred_category_from_events(request) or _infer_preferred_category(customer)
    if inferred_category and not context.get('preferred_category'):
        context['preferred_category'] = inferred_category

    chat_session, _ = AIChatSession.objects.get_or_create(
        customer=customer,
        session_id=session_id,
        defaults={'source': 'widget'},
    )
    AIChatMessage.objects.create(
        session=chat_session,
        role='user',
        message_type='chat_question',
        content=question,
        metadata={'context': context},
    )

    if _use_advanced_ai_widget():
        advanced_client = AIBehaviorClient()
        _push_advanced_behavior_events(
            advanced_client=advanced_client,
            customer_id=customer.id,
            session_id=session_id,
            session_events=session_events + ['web_chat_opened', 'web_chat_question'],
            viewed_product_ids=viewed_product_ids,
            question=question,
        )
        try:
            advanced_chat = advanced_client.chat(
                user_id=customer.id,
                question=question,
                session_id=session_id,
                context=context,
            )
        except AIBehaviorServiceUnavailable as exc:
            AIChatMessage.objects.create(
                session=chat_session,
                role='system',
                message_type='error',
                content=str(exc),
                metadata={'status_code': 503, 'source': 'advanced-ai'},
            )
            return JsonResponse({'error': str(exc)}, status=503)
        except AIBehaviorServiceError as exc:
            AIChatMessage.objects.create(
                session=chat_session,
                role='system',
                message_type='error',
                content=str(exc),
                metadata={'status_code': 400, 'source': 'advanced-ai'},
            )
            return JsonResponse({'error': str(exc)}, status=400)

        recommended_ids = advanced_chat.get('recommended_products', []) if isinstance(advanced_chat, dict) else []
        behavior_info = {}
        if not recommended_ids:
            try:
                advanced_recommend = advanced_client.recommend(
                    user_id=customer.id,
                    top_k=3,
                    candidate_products=catalog_hints,
                )
                behavior_info = {
                    'purchase_propensity': advanced_recommend.get('purchase_propensity'),
                    'category_trends': advanced_recommend.get('category_trends', []),
                }
                recommended_ids = [
                    int(item.get('product_id'))
                    for item in advanced_recommend.get('recommendations', [])
                    if isinstance(item, dict) and item.get('product_id') is not None
                ]
            except (AIBehaviorServiceUnavailable, AIBehaviorServiceError, TypeError, ValueError):
                recommended_ids = []

        rag_chunks = advanced_chat.get('rag_chunks', []) if isinstance(advanced_chat, dict) else []
        response = {
            'answer': advanced_chat.get('answer', ''),
            'citations': [chunk.get('node') for chunk in rag_chunks if isinstance(chunk, dict) and chunk.get('node')],
            'recommended_products': recommended_ids,
            'recommended_product_items': _serialize_recommended_products(recommended_ids),
            'intent': 'advanced_ai_chat',
            'source': advanced_chat.get('source', 'advanced-ai'),
            'gnn_trends': advanced_chat.get('gnn_trends', []),
        }
        if behavior_info:
            response['behavior'] = behavior_info

        AIChatMessage.objects.create(
            session=chat_session,
            role='assistant',
            message_type='chat_answer',
            content=response.get('answer', ''),
            metadata={
                'citations': response.get('citations', []),
                'recommended_products': response.get('recommended_products', []),
                'recommended_product_items': response.get('recommended_product_items', []),
                'intent': response.get('intent', 'advanced_ai_chat'),
                'source': response.get('source', 'advanced-ai'),
            },
        )

        return JsonResponse(response)

    rag_client = RAGClient()
    behavior_client = BehaviorClient()

    behavior_result = {}
    try:
        behavior_result = behavior_client.score(
            user_id=customer.id,
            session_events=session_events + ['web_chat_opened', 'web_chat_question'],
            context={
                'surface': 'web_widget',
                'preferred_category': context.get('preferred_category'),
                'budget_max': context.get('budget_max'),
                'query_text': question,
            }
        )
    except (BehaviorServiceUnavailable, BehaviorServiceError):
        behavior_result = {}

    try:
        rag_result = rag_client.query_chat(
            session_id=session_id,
            user_id=customer.id,
            question=question,
            context=context,
        )
    except RAGServiceUnavailable as exc:
        AIChatMessage.objects.create(
            session=chat_session,
            role='system',
            message_type='error',
            content=str(exc),
            metadata={'status_code': 503},
        )
        return JsonResponse({'error': str(exc)}, status=503)
    except RAGServiceError as exc:
        AIChatMessage.objects.create(
            session=chat_session,
            role='system',
            message_type='error',
            content=str(exc),
            metadata={'status_code': 400},
        )
        return JsonResponse({'error': str(exc)}, status=400)

    recommended_ids = rag_result.get('recommended_products', []) if isinstance(rag_result, dict) else []
    if not recommended_ids:
        try:
            behavior_recommend = behavior_client.recommend(
                user_id=customer.id,
                candidate_product_ids=viewed_product_ids + [item['id'] for item in catalog_hints],
                candidate_products=catalog_hints,
                top_k=3,
                context={
                    'preferred_category': context.get('preferred_category'),
                    'budget_max': context.get('budget_max'),
                    'session_events': session_events + ['web_chat_opened', 'web_chat_question'],
                    'query_text': question,
                },
            )
            recommended_ids = [
                int(item.get('product_id'))
                for item in behavior_recommend.get('recommendations', [])
                if isinstance(item, dict) and item.get('product_id') is not None
            ]
        except (BehaviorServiceUnavailable, BehaviorServiceError, TypeError, ValueError):
            recommended_ids = []

    response = {
        'answer': rag_result.get('answer', ''),
        'citations': rag_result.get('citations', []),
        'recommended_products': recommended_ids,
        'recommended_product_items': _serialize_recommended_products(recommended_ids),
        'intent': rag_result.get('intent', 'unknown'),
    }
    if behavior_result:
        response['behavior'] = {
            'purchase_propensity': behavior_result.get('purchase_propensity'),
            'next_best_categories': behavior_result.get('next_best_categories', []),
            'value_band': behavior_result.get('value_band'),
        }

    AIChatMessage.objects.create(
        session=chat_session,
        role='assistant',
        message_type='chat_answer',
        content=response.get('answer', ''),
        metadata={
            'citations': response.get('citations', []),
            'recommended_products': response.get('recommended_products', []),
            'recommended_product_items': response.get('recommended_product_items', []),
            'intent': response.get('intent', 'unknown'),
        },
    )

    return JsonResponse(response)


@login_required(login_url='login')
@require_POST
def ai_recommend_widget(request):
    customer, _ = Customer.objects.get_or_create(
        user=request.user,
        defaults={'name': request.user.username, 'email': request.user.email}
    )

    try:
        payload = json.loads(request.body.decode('utf-8')) if request.body else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'Invalid JSON payload'}, status=400)

    top_k = payload.get('top_k', 5)
    candidate_product_ids = payload.get('candidate_product_ids', [])
    question = (payload.get('question') or '').strip()
    session_events = build_session_event_signals(request, limit=30)
    viewed_product_ids = get_recently_viewed_product_ids(request, limit=12)
    viewed_hints = _catalog_hints_from_product_ids(viewed_product_ids)
    query_hints = _build_catalog_hints(question)
    catalog_hints = _merge_catalog_hints(viewed_hints, query_hints, top_k=30)

    if not isinstance(candidate_product_ids, list) or not candidate_product_ids:
        candidate_product_ids = viewed_product_ids + [item['id'] for item in catalog_hints]

    session_id = (payload.get('session_id') or f'web-user-{request.user.id}-recommend')[:120]
    chat_session, _ = AIChatSession.objects.get_or_create(
        customer=customer,
        session_id=session_id,
        defaults={'source': 'widget'},
    )

    if _use_advanced_ai_widget():
        advanced_client = AIBehaviorClient()
        _push_advanced_behavior_events(
            advanced_client=advanced_client,
            customer_id=customer.id,
            session_id=session_id,
            session_events=session_events + ['web_widget_recommendation'],
            viewed_product_ids=viewed_product_ids,
            question=question,
        )
        try:
            result = advanced_client.recommend(
                user_id=customer.id,
                top_k=int(top_k),
                candidate_products=catalog_hints,
            )
            raw_recommendations = result.get('recommendations', []) if isinstance(result, dict) else []
            product_ids = []
            for item in raw_recommendations:
                if not isinstance(item, dict):
                    continue
                try:
                    product_ids.append(int(item.get('product_id')))
                except (TypeError, ValueError):
                    continue

            result['recommended_product_items'] = _serialize_recommended_products(product_ids)
            AIChatMessage.objects.create(
                session=chat_session,
                role='assistant',
                message_type='recommendation',
                content='Advanced AI recommendation response generated',
                metadata={
                    'top_k': int(top_k),
                    'recommendations': result.get('recommendations', []),
                    'recommended_product_items': result.get('recommended_product_items', []),
                    'source': 'advanced-ai',
                },
            )
            return JsonResponse(result)
        except AIBehaviorServiceUnavailable as exc:
            AIChatMessage.objects.create(
                session=chat_session,
                role='system',
                message_type='error',
                content=str(exc),
                metadata={'status_code': 503, 'source': 'advanced-ai'},
            )
            return JsonResponse({'error': str(exc)}, status=503)
        except AIBehaviorServiceError as exc:
            AIChatMessage.objects.create(
                session=chat_session,
                role='system',
                message_type='error',
                content=str(exc),
                metadata={'status_code': 400, 'source': 'advanced-ai'},
            )
            return JsonResponse({'error': str(exc)}, status=400)

    client = BehaviorClient()
    try:
        result = client.recommend(
            user_id=customer.id,
            candidate_product_ids=candidate_product_ids,
            candidate_products=catalog_hints,
            context={
                'preferred_category': infer_preferred_category_from_events(request) or _infer_preferred_category(customer),
                'session_events': session_events + ['web_widget_recommendation'],
                'query_text': question,
            },
            top_k=int(top_k),
        )
        raw_recommendations = result.get('recommendations', []) if isinstance(result, dict) else []
        product_ids = []
        for item in raw_recommendations:
            if not isinstance(item, dict):
                continue
            try:
                product_ids.append(int(item.get('product_id')))
            except (TypeError, ValueError):
                continue

        result['recommended_product_items'] = _serialize_recommended_products(product_ids)
        AIChatMessage.objects.create(
            session=chat_session,
            role='assistant',
            message_type='recommendation',
            content='Recommendation response generated',
            metadata={
                'top_k': int(top_k),
                'recommendations': result.get('recommendations', []),
                'recommended_product_items': result.get('recommended_product_items', []),
            },
        )
        return JsonResponse(result)
    except BehaviorServiceUnavailable as exc:
        AIChatMessage.objects.create(
            session=chat_session,
            role='system',
            message_type='error',
            content=str(exc),
            metadata={'status_code': 503},
        )
        return JsonResponse({'error': str(exc)}, status=503)
    except BehaviorServiceError as exc:
        AIChatMessage.objects.create(
            session=chat_session,
            role='system',
            message_type='error',
            content=str(exc),
            metadata={'status_code': 400},
        )
        return JsonResponse({'error': str(exc)}, status=400)


@login_required(login_url='login')
@require_POST
def ai_train_model_widget(request):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Forbidden'}, status=403)

    try:
        payload = json.loads(request.body.decode('utf-8')) if request.body else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'Invalid JSON payload'}, status=400)

    min_events = payload.get('min_events', 50)
    try:
        min_events = int(min_events)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid min_events'}, status=400)

    client = AIBehaviorClient()
    try:
        result = client.train(min_events=min_events)
        return JsonResponse(result)
    except AIBehaviorServiceUnavailable as exc:
        return JsonResponse({'error': str(exc)}, status=503)
    except AIBehaviorServiceError as exc:
        return JsonResponse({'error': str(exc)}, status=400)
