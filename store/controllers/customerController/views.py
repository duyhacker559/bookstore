from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q, Max
from django.utils import timezone
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import datetime
from store.models.customer.customer import Customer
from store.models.order.order import Order
from store.models.order.order_item import OrderItem
from store.models.user_profile import UserProfile
from store.models.book.book import Book
from store.models.rating.rating import Comment
from store.models.communication import UserNotification, InboxMessage, InboxReply
from store.services.notification_service import create_user_notification
from decimal import Decimal


MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 2MB
ALLOWED_AVATAR_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


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
    return render(request, 'customer/notifications.html', {
        'notifications': notifications_qs,
    })


@login_required(login_url='login')
def notification_updates(request):
    customer = Customer.objects.filter(user=request.user).first()
    unread_count = 0
    inbox_available_count = 0
    if customer:
        unread_count = UserNotification.objects.filter(customer=customer, is_read=False).count()
        inbox_available_count = UserNotification.objects.filter(
            customer=customer,
            is_read=False,
            link__startswith='/customer/inbox/',
        ).count()
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
    prefill_book = None
    thread_state = request.GET.get('thread_state', 'all').strip()
    book_id = request.GET.get('book_id', '').strip()
    if book_id:
        try:
            prefill_book = Book.objects.filter(id=int(book_id)).first()
        except ValueError:
            prefill_book = None

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

    messages_qs = (
        InboxMessage.objects.filter(customer=customer)
        .select_related('book')
        .prefetch_related('replies')
        .order_by('-created_at')
    )

    message_list = list(messages_qs)
    for message_item in message_list:
        replies = list(message_item.replies.all())
        message_item.reply_count = len(replies)
        message_item.last_reply = replies[-1] if replies else None

    if thread_state == 'awaiting_staff':
        message_list = [
            m for m in message_list
            if m.last_reply is not None and m.last_reply.sender_type == 'customer'
        ]
    elif thread_state == 'awaiting_you':
        message_list = [
            m for m in message_list
            if m.last_reply is not None and m.last_reply.sender_type == 'staff'
        ]

    paginator = Paginator(message_list, 10)
    page_number = request.GET.get('page', 1)
    inbox_page = paginator.get_page(page_number)
    inbox_unread_count, inbox_latest_activity = _customer_inbox_activity_snapshot(customer)

    return render(request, 'customer/inbox.html', {
        'inbox_messages': inbox_page,
        'inbox_page': inbox_page,
        'prefill_book': prefill_book,
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
