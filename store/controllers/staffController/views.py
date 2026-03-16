from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q, Sum, Count, F, Min, Max, Avg
from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta, datetime

from store.events import publish_event
from store.models import Shipment, Staff, Book, Order, OrderItem, Category, Rating, Comment, InboxMessage, InboxReply
from store.models.communication import UserNotification
from store.models.book.book_image import BookImage
from store.shipping_client import ShippingClient, ShippingProcessingError, ShippingServiceUnavailable
from store.services.notification_service import create_user_notification


ALLOWED_SHIPMENT_STATUSES = {
    "pending": "Pending",
    "processing": "Processing",
    "shipped": "Shipped",
    "delivered": "Delivered",
    "failed": "Failed",
}

shipping_client = ShippingClient()


def _staff_inbox_activity_snapshot():
    unread_count = InboxMessage.objects.filter(status="unread").count()
    latest_reply = InboxReply.objects.aggregate(last=Max("created_at"))["last"]
    latest_message = InboxMessage.objects.aggregate(last=Max("created_at"))["last"]
    latest_candidates = [dt for dt in [latest_reply, latest_message] if dt is not None]
    latest_activity = max(latest_candidates) if latest_candidates else None
    latest_token = latest_activity.isoformat() if latest_activity else ""
    return unread_count, latest_token


def _resolve_categories_from_request(request):
    selected_ids = [value for value in request.POST.getlist("categories") if value]
    selected_categories = list(Category.objects.filter(id__in=selected_ids).order_by("name"))

    existing_names = {category.name.lower(): category for category in selected_categories}
    custom_categories = request.POST.get("custom_categories", "")
    for raw_name in custom_categories.split(","):
        name = raw_name.strip()
        if not name:
            continue
        key = name.lower()
        if key in existing_names:
            continue
        category_obj, _ = Category.objects.get_or_create(name=name)
        selected_categories.append(category_obj)
        existing_names[key] = category_obj

    return selected_categories


def _sync_legacy_book_categories(book, categories):
    primary_category = categories[0] if categories else None
    book.category_fk = primary_category
    book.category = primary_category.name if primary_category else ""


def is_staff_user(user):
    """Check if user is staff (has Staff model record or is Django staff)."""
    if not user.is_authenticated:
        return False
    # Check Django's built-in is_staff flag or custom Staff model
    return user.is_staff or Staff.objects.filter(user=user).exists()


@login_required(login_url="login")
@user_passes_test(is_staff_user, login_url="login")
def staff_home(request):
    shipments_qs = Shipment.objects.select_related("order").order_by("-id")
    total_shipments = shipments_qs.count()
    pending_count = shipments_qs.filter(status__iexact="Pending").count()
    processing_count = shipments_qs.filter(status__iexact="Processing").count()
    shipped_count = shipments_qs.filter(status__iexact="Shipped").count()
    delivered_count = shipments_qs.filter(status__iexact="Delivered").count()

    total_books = Book.objects.count()
    low_stock = Book.objects.filter(stock__lte=5).count()
    return render(
        request,
        "staff/home.html",
        {
            "total_shipments": total_shipments,
            "pending_count": pending_count,
            "processing_count": processing_count,
            "shipped_count": shipped_count,
            "delivered_count": delivered_count,
            "recent_shipments": shipments_qs[:6],
            "total_books": total_books,
            "low_stock": low_stock,
        },
    )


@login_required(login_url="login")
@user_passes_test(is_staff_user, login_url="login")
def manage_shipments(request):
    shipments = Shipment.objects.select_related("order", "order__customer", "order__customer__user").order_by("-id")
    status_filter = request.GET.get("status", "").strip().lower()
    query = request.GET.get("q", "").strip()

    if status_filter in ALLOWED_SHIPMENT_STATUSES:
        shipments = shipments.filter(status__iexact=ALLOWED_SHIPMENT_STATUSES[status_filter])

    if query:
        shipments = shipments.filter(
            Q(id__icontains=query)
            | Q(order__id__icontains=query)
            | Q(order__customer__name__icontains=query)
            | Q(order__customer__user__username__icontains=query)
        )

    return render(
        request,
        "staff/shipments.html",
        {
            "shipments": shipments,
            "status_choices": ALLOWED_SHIPMENT_STATUSES,
            "selected_status": status_filter,
            "search_query": query,
        },
    )


@login_required(login_url="login")
@user_passes_test(is_staff_user, login_url="login")
def update_shipment_status(request, shipment_id):
    if request.method != "POST":
        return redirect("staff_manage_shipments")

    shipment = get_object_or_404(Shipment, id=shipment_id)
    requested_status = request.POST.get("status", "").strip().lower()
    if requested_status not in ALLOWED_SHIPMENT_STATUSES:
        messages.error(request, "Invalid shipment status")
        return redirect("staff_manage_shipments")

    local_status = ALLOWED_SHIPMENT_STATUSES[requested_status]

    try:
        remote_result = shipping_client.update_shipment_status(str(shipment.order.id), requested_status)
        remote_status = remote_result.get("current_status", requested_status)
        local_status = ALLOWED_SHIPMENT_STATUSES.get(remote_status.lower(), local_status)
        messages.success(request, f"Shipment {shipment.id} synced to Shipping Service as {local_status}")
    except ShippingProcessingError as e:
        # 404 means shipment doesn't exist in service (legacy data before microservice integration)
        messages.info(request, f"Shipment {shipment.id} updated locally (legacy order, not in Shipping Service)")
    except ShippingServiceUnavailable:
        messages.warning(request, f"Shipping Service unavailable. Updated shipment {shipment.id} locally")

    shipment.status = local_status
    shipment.save(update_fields=["status"])

    create_user_notification(
        shipment.order.customer,
        title=f"Shipment Update for Order #{shipment.order.id}",
        message=f"Your shipment status is now {local_status}.",
        notification_type="shipping",
        link=f"/order/{shipment.order.id}/track/",
    )

    publish_event(
        "shipment.updated",
        {
            "shipment_id": shipment.id,
            "order_id": shipment.order.id,
            "status": requested_status,
        },
    )

    return redirect("staff_manage_shipments")


# ─── Book Management ─────────────────────────────────────────────────────────

@login_required(login_url="login")
@user_passes_test(is_staff_user, login_url="login")
def staff_books(request):
    books = Book.objects.prefetch_related("images", "categories_m2m").all()
    query = request.GET.get("q", "").strip()
    if query:
        books = books.filter(
            Q(title__icontains=query)
            | Q(author__icontains=query)
            | Q(category__icontains=query)
            | Q(category_fk__name__icontains=query)
            | Q(categories_m2m__name__icontains=query)
        )
    
    # Price range filter
    price_min = request.GET.get("price_min", "").strip()
    price_max = request.GET.get("price_max", "").strip()
    if price_min:
        try:
            books = books.filter(price__gte=float(price_min))
        except ValueError:
            pass
    if price_max:
        try:
            books = books.filter(price__lte=float(price_max))
        except ValueError:
            pass
    
    # Category filter
    category = request.GET.get("category", "").strip()
    if category:
        books = books.filter(
            Q(categories_m2m__name__iexact=category)
            | Q(category__icontains=category)
            | Q(category_fk__name__iexact=category)
        )
    
    # Stock level filter
    stock_level = request.GET.get("stock_level", "").strip()
    if stock_level == "low":
        books = books.filter(stock__lte=5)
    elif stock_level == "medium":
        books = books.filter(stock__gt=5, stock__lte=20)
    elif stock_level == "high":
        books = books.filter(stock__gt=20)
    elif stock_level == "out":
        books = books.filter(stock__lte=0)
    
    sort = request.GET.get("sort", "")
    sort_map = {
        "price": "price", "-price": "-price",
        "stock": "stock", "-stock": "-stock",
        "title": "title", "-title": "-title",
    }
    books = books.distinct().order_by(sort_map.get(sort, "-id"))
    
    # Get categories for filter dropdown and forms
    categories = Category.objects.order_by("name")
    
    # Get price range stats
    price_stats = books.aggregate(min_price=Min("price"), max_price=Max("price"))
    
    book_list = list(books)
    for book in book_list:
        cover = book.images.filter(is_cover=True).first() or book.images.first()
        book.cover_image = cover.image.url if cover and cover.image else ""
        book.category_ids_csv = ",".join(str(category_obj.id) for category_obj in book.categories_m2m.all())
    
    return render(request, "staff/books.html", {
        "books": book_list,
        "query": query,
        "sort": sort,
        "category": category,
        "price_min": price_min,
        "price_max": price_max,
        "stock_level": stock_level,
        "categories": categories,
        "min_price": price_stats.get("min_price") or 0,
        "max_price": price_stats.get("max_price") or 100,
        "total_books": Book.objects.count(),
        "low_stock": Book.objects.filter(stock__lte=5).count(),
    })


@login_required(login_url="login")
@user_passes_test(is_staff_user, login_url="login")
def staff_add_book(request):
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        author = request.POST.get("author", "").strip()
        price = request.POST.get("price", "0").strip()
        stock = request.POST.get("stock", "0").strip()
        description = request.POST.get("description", "").strip()
        categories = _resolve_categories_from_request(request)
        if not title or not author:
            messages.error(request, "Title and author are required.")
            return redirect("staff_books")
        try:
            book = Book.objects.create(
                title=title,
                author=author,
                price=price,
                stock=int(stock),
                description=description,
            )
            _sync_legacy_book_categories(book, categories)
            book.save(update_fields=["category", "category_fk"])
            book.categories_m2m.set(categories)
            if request.FILES.get("image"):
                BookImage.objects.create(book=book, image=request.FILES["image"], is_cover=True)
            messages.success(request, f"Book \u201c{title}\u201d added successfully.")
        except Exception as e:
            messages.error(request, f"Could not add book: {e}")
        return redirect("staff_books")
    return redirect("staff_books")


@login_required(login_url="login")
@user_passes_test(is_staff_user, login_url="login")
def staff_edit_book(request, book_id):
    book = get_object_or_404(Book.objects.prefetch_related("categories_m2m"), id=book_id)
    if request.method == "POST":
        categories = _resolve_categories_from_request(request)
        book.title = request.POST.get("title", book.title).strip()
        book.author = request.POST.get("author", book.author).strip()
        book.price = request.POST.get("price", book.price)
        book.stock = int(request.POST.get("stock", book.stock))
        book.description = request.POST.get("description", book.description).strip()
        _sync_legacy_book_categories(book, categories)
        book.save()
        book.categories_m2m.set(categories)
        if request.FILES.get("image"):
            BookImage.objects.filter(book=book, is_cover=True).delete()
            BookImage.objects.create(book=book, image=request.FILES["image"], is_cover=True)
        messages.success(request, f"Book \u201c{book.title}\u201d updated.")
        return redirect("staff_books")
    cover = book.images.filter(is_cover=True).first() or book.images.first()
    book.cover_image = cover.image.url if cover and cover.image else ""
    return render(request, "staff/book_form.html", {"book": book, "action": "Edit"})


@login_required(login_url="login")
@user_passes_test(is_staff_user, login_url="login")
def staff_delete_book(request, book_id):
    if request.method == "POST":
        book = get_object_or_404(Book, id=book_id)
        title = book.title
        book.delete()
        messages.success(request, f"Book \u201c{title}\u201d deleted.")
    return redirect("staff_books")


def _recalculate_book_feedback(book_ids):
    """Refresh denormalized rating/review_count values on books after moderation changes."""
    for book in Book.objects.filter(id__in=book_ids):
        avg_rating = Rating.objects.filter(book=book, is_hidden=False).aggregate(avg=Avg("score"))["avg"] or 0
        review_count = Comment.objects.filter(book=book, is_hidden=False).count()
        book.rating = round(float(avg_rating), 1)
        book.review_count = review_count
        book.save(update_fields=["rating", "review_count"])


@login_required(login_url="login")
@user_passes_test(is_staff_user, login_url="login")
def staff_feedback_moderation(request):
    if request.method == "POST":
        target = request.POST.get("target", "").strip()
        action = request.POST.get("action", "").strip()

        if target == "rating":
            selected_ids = request.POST.getlist("selected_ratings")
            queryset = Rating.objects.filter(id__in=selected_ids)
        elif target == "comment":
            selected_ids = request.POST.getlist("selected_comments")
            queryset = Comment.objects.filter(id__in=selected_ids)
        else:
            selected_ids = []
            queryset = None

        if not selected_ids:
            messages.warning(request, "Select at least one item to moderate.")
            return redirect("staff_feedback_moderation")

        if queryset is None:
            messages.error(request, "Invalid moderation target.")
            return redirect("staff_feedback_moderation")

        affected_book_ids = list(queryset.values_list("book_id", flat=True).distinct())

        affected_customers = list(queryset.values_list("customer", flat=True).distinct())

        if action == "hide":
            updated = queryset.update(is_hidden=True)
            messages.success(request, f"Hidden {updated} {target}(s).")
        elif action == "unhide":
            updated = queryset.update(is_hidden=False)
            messages.success(request, f"Unhidden {updated} {target}(s).")
        elif action == "delete":
            deleted_count = queryset.count()
            queryset.delete()
            messages.success(request, f"Deleted {deleted_count} {target}(s).")
        else:
            messages.error(request, "Invalid action.")
            return redirect("staff_feedback_moderation")

        _recalculate_book_feedback(affected_book_ids)

        action_label = {
            "hide": "hidden",
            "unhide": "restored",
            "delete": "removed",
        }.get(action, "updated")
        for customer_id in affected_customers:
            if target == "rating":
                notif_title = "Rating Moderation Notice"
            else:
                notif_title = "Review Moderation Notice"

            from store.models.customer.customer import Customer
            customer_obj = Customer.objects.filter(id=customer_id).first()
            if not customer_obj:
                continue

            create_user_notification(
                customer_obj,
                title=notif_title,
                message=f"One or more of your {target}s were {action_label} by moderation staff.",
                notification_type="moderation",
                link="/customer/notifications/",
            )

        return redirect("staff_feedback_moderation")

    query = request.GET.get("q", "").strip()
    rating_score = request.GET.get("rating_score", "").strip()
    rating_visibility = request.GET.get("rating_visibility", "all").strip()
    comment_visibility = request.GET.get("comment_visibility", "all").strip()
    verified = request.GET.get("verified", "all").strip()

    ratings = Rating.objects.select_related("customer", "book").order_by("-updated_at")
    comments = Comment.objects.select_related("customer", "book", "rating").order_by("-updated_at")

    if query:
        ratings = ratings.filter(
            Q(customer__name__icontains=query) | Q(book__title__icontains=query)
        )
        comments = comments.filter(
            Q(customer__name__icontains=query)
            | Q(book__title__icontains=query)
            | Q(title__icontains=query)
            | Q(content__icontains=query)
        )

    if rating_score:
        try:
            ratings = ratings.filter(score=int(rating_score))
        except ValueError:
            pass

    if rating_visibility == "visible":
        ratings = ratings.filter(is_hidden=False)
    elif rating_visibility == "hidden":
        ratings = ratings.filter(is_hidden=True)

    if comment_visibility == "visible":
        comments = comments.filter(is_hidden=False)
    elif comment_visibility == "hidden":
        comments = comments.filter(is_hidden=True)

    if verified == "verified":
        comments = comments.filter(is_verified_purchase=True)
    elif verified == "unverified":
        comments = comments.filter(is_verified_purchase=False)

    return render(request, "staff/feedback_moderation.html", {
        "ratings": ratings[:100],
        "comments": comments[:100],
        "query": query,
        "rating_score": rating_score,
        "rating_visibility": rating_visibility,
        "comment_visibility": comment_visibility,
        "verified": verified,
    })


@login_required(login_url="login")
@user_passes_test(is_staff_user, login_url="login")
def staff_inbox(request):
    if request.method == "POST":
        message_id = request.POST.get("message_id", "").strip()
        action = request.POST.get("action", "").strip()
        staff_note = request.POST.get("staff_note", "").strip()
        message_obj = get_object_or_404(InboxMessage, id=message_id)

        if action == "mark_read":
            message_obj.status = "read"
            message_obj.read_at = timezone.now()
            if staff_note:
                message_obj.staff_note = staff_note
            message_obj.save(update_fields=["status", "read_at", "staff_note"])
            create_user_notification(
                message_obj.customer,
                title="Inbox Message Reviewed",
                message=f"Staff reviewed your message: {message_obj.subject}",
                notification_type="system",
                link="/customer/inbox/",
            )
        elif action == "reply":
            if not staff_note:
                messages.error(request, "Reply note is required for reply action.")
                return redirect("staff_inbox")
            InboxReply.objects.create(
                inbox_message=message_obj,
                sender_type="staff",
                content=staff_note,
            )
            message_obj.status = "read"
            message_obj.read_at = timezone.now()
            message_obj.staff_note = staff_note
            message_obj.save(update_fields=["status", "read_at", "staff_note"])
            create_user_notification(
                message_obj.customer,
                title="New Chat Reply Available",
                message=f"Staff replied to '{message_obj.subject}'. Open the chat to continue.",
                notification_type="system",
                link=f"/customer/inbox/{message_obj.id}/",
            )
        elif action == "mark_unread":
            message_obj.status = "unread"
            message_obj.read_at = None
            if staff_note:
                message_obj.staff_note = staff_note
            message_obj.save(update_fields=["status", "read_at", "staff_note"])

        return redirect("staff_inbox")

    status_filter = request.GET.get("status", "all").strip()
    query = request.GET.get("q", "").strip()
    thread_state = request.GET.get("thread_state", "all").strip()
    sort_mode = request.GET.get("sort", "needs_staff").strip()

    messages_qs = (
        InboxMessage.objects.select_related("customer", "book", "customer__user")
        .prefetch_related("replies")
        .order_by("-created_at")
    )
    if status_filter in {"read", "unread"}:
        messages_qs = messages_qs.filter(status=status_filter)
    if query:
        messages_qs = messages_qs.filter(
            Q(subject__icontains=query)
            | Q(content__icontains=query)
            | Q(customer__name__icontains=query)
            | Q(book__title__icontains=query)
        )

    unread_count = InboxMessage.objects.filter(status="unread").count()
    read_count = InboxMessage.objects.filter(status="read").count()
    staff_inbox_unread_count, staff_inbox_latest_activity = _staff_inbox_activity_snapshot()

    message_list = list(messages_qs)
    for message_item in message_list:
        replies = list(message_item.replies.all())
        message_item.reply_count = len(replies)
        message_item.last_reply = replies[-1] if replies else None
        message_item.needs_staff_action = bool(
            message_item.last_reply is not None and message_item.last_reply.sender_type == "customer"
        )
        message_item.waiting_customer = bool(
            message_item.last_reply is not None and message_item.last_reply.sender_type == "staff"
        )

    if thread_state == "needs_staff":
        message_list = [
            m for m in message_list
            if m.needs_staff_action
        ]
    elif thread_state == "waiting_customer":
        message_list = [
            m for m in message_list
            if m.waiting_customer
        ]

    if sort_mode == "oldest":
        message_list = sorted(message_list, key=lambda m: m.created_at)
    elif sort_mode == "newest":
        message_list = sorted(message_list, key=lambda m: m.created_at, reverse=True)
    else:
        message_list = sorted(
            message_list,
            key=lambda m: (not m.needs_staff_action, -m.created_at.timestamp()),
        )

    paginator = Paginator(message_list, 20)
    page_number = request.GET.get("page", 1)
    inbox_page = paginator.get_page(page_number)

    return render(request, "staff/inbox.html", {
        "inbox_messages": inbox_page,
        "inbox_page": inbox_page,
        "status_filter": status_filter,
        "thread_state": thread_state,
        "sort_mode": sort_mode,
        "search_query": query,
        "unread_count": unread_count,
        "read_count": read_count,
        "staff_inbox_unread_count": staff_inbox_unread_count,
        "staff_inbox_latest_activity": staff_inbox_latest_activity,
    })


@login_required(login_url="login")
@user_passes_test(is_staff_user, login_url="login")
def staff_inbox_thread(request, message_id):
    message_obj = get_object_or_404(
        InboxMessage.objects.select_related("customer", "book").prefetch_related("replies"),
        id=message_id,
    )

    if request.method == "POST":
        action = request.POST.get("action", "").strip()
        reply_content = request.POST.get("reply_content", "").strip()

        if action == "reply":
            if not reply_content:
                messages.error(request, "Reply note is required.")
                return redirect("staff_inbox_thread", message_id=message_obj.id)

            InboxReply.objects.create(
                inbox_message=message_obj,
                sender_type="staff",
                content=reply_content,
            )
            message_obj.staff_note = reply_content
            message_obj.status = "read"
            message_obj.read_at = timezone.now()
            message_obj.save(update_fields=["staff_note", "status", "read_at"])
            # Clear old notifications about this inbox message to prevent pile-up
            UserNotification.objects.filter(
                customer=message_obj.customer,
                link=f"/customer/inbox/{message_obj.id}/",
            ).delete()
            # Create fresh notification for this reply
            create_user_notification(
                message_obj.customer,
                title="New Chat Reply Available",
                message=f"Staff replied to '{message_obj.subject}'. Open the chat to continue.",
                notification_type="system",
                link=f"/customer/inbox/{message_obj.id}/",
            )
        elif action == "mark_read":
            message_obj.status = "read"
            message_obj.read_at = timezone.now()
            message_obj.save(update_fields=["status", "read_at"])
        elif action == "mark_unread":
            message_obj.status = "unread"
            message_obj.read_at = None
            message_obj.save(update_fields=["status", "read_at"])

        return redirect("staff_inbox_thread", message_id=message_obj.id)

    staff_inbox_unread_count, staff_inbox_latest_activity = _staff_inbox_activity_snapshot()

    latest_thread_reply = message_obj.replies.aggregate(last=Max("created_at"))["last"]

    return render(request, "staff/inbox_thread.html", {
        "inbox_message": message_obj,
        "staff_inbox_unread_count": staff_inbox_unread_count,
        "staff_inbox_latest_activity": staff_inbox_latest_activity,
        "thread_latest_activity": latest_thread_reply.isoformat() if latest_thread_reply else "",
    })


@login_required(login_url="login")
@user_passes_test(is_staff_user, login_url="login")
def staff_inbox_updates(request):
    unread_count, latest_token = _staff_inbox_activity_snapshot()
    return JsonResponse({
        "unread_count": unread_count,
        "latest_activity": latest_token,
    })


@login_required(login_url="login")
@user_passes_test(is_staff_user, login_url="login")
def staff_inbox_thread_updates(request, message_id):
    message_obj = get_object_or_404(
        InboxMessage.objects.select_related("customer", "book").prefetch_related("replies"),
        id=message_id,
    )
    latest_thread_reply = message_obj.replies.aggregate(last=Max("created_at"))["last"]
    replies_html = render_to_string("staff/_inbox_replies.html", {
        "inbox_message": message_obj,
    }, request=request)

    return JsonResponse({
        "latest_activity": latest_thread_reply.isoformat() if latest_thread_reply else "",
        "status": message_obj.status,
        "replies_html": replies_html,
    })


# ─── Analytics ───────────────────────────────────────────────────────────────

@login_required(login_url="login")
@user_passes_test(is_staff_user, login_url="login")
def staff_analytics(request):
    now = timezone.now()
    today = timezone.localdate()

    range_key = request.GET.get("range", "30d")
    start_raw = (request.GET.get("start") or "").strip()
    end_raw = (request.GET.get("end") or "").strip()

    preset_days = {"7d": 7, "30d": 30, "90d": 90}
    if range_key in preset_days:
        days = preset_days[range_key]
        period_end = today
        period_start = today - timedelta(days=days - 1)
    elif range_key == "custom" and start_raw and end_raw:
        try:
            period_start = datetime.strptime(start_raw, "%Y-%m-%d").date()
            period_end = datetime.strptime(end_raw, "%Y-%m-%d").date()
            if period_start > period_end:
                period_start, period_end = period_end, period_start
        except ValueError:
            range_key = "30d"
            period_end = today
            period_start = today - timedelta(days=29)
    else:
        range_key = "30d"
        period_end = today
        period_start = today - timedelta(days=29)

    period_days = (period_end - period_start).days + 1
    previous_end = period_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=period_days - 1)

    all_orders = Order.objects.all()
    period_orders = all_orders.filter(created_at__date__gte=period_start, created_at__date__lte=period_end)
    previous_orders = all_orders.filter(created_at__date__gte=previous_start, created_at__date__lte=previous_end)

    period_revenue = period_orders.aggregate(r=Sum("total_amount"))["r"] or 0
    period_order_count = period_orders.count()
    period_customer_count = period_orders.values("customer").distinct().count()
    avg_order_value = (float(period_revenue) / period_order_count) if period_order_count else 0

    prev_revenue = previous_orders.aggregate(r=Sum("total_amount"))["r"] or 0
    prev_order_count = previous_orders.count()
    prev_avg_order_value = (float(prev_revenue) / prev_order_count) if prev_order_count else 0

    def _delta_pct(current, previous):
        current = float(current or 0)
        previous = float(previous or 0)
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round(((current - previous) / previous) * 100, 1)

    revenue_delta = _delta_pct(period_revenue, prev_revenue)
    orders_delta = _delta_pct(period_order_count, prev_order_count)
    avg_delta = _delta_pct(avg_order_value, prev_avg_order_value)

    total_books = Book.objects.count()
    total_customers = all_orders.values("customer").distinct().count()
    inbox_unread_count = InboxMessage.objects.filter(status="unread").count()
    inbox_read_count = InboxMessage.objects.filter(status="read").count()

    orders_by_status = (
        period_orders.values("status")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    top_books = (
        OrderItem.objects
        .filter(order__created_at__date__gte=period_start, order__created_at__date__lte=period_end)
        .values("book__title", "book__author", "book__id")
        .annotate(units_sold=Sum("quantity"), revenue=Sum(F("quantity") * F("price")))
        .order_by("-units_sold")[:10]
    )

    low_stock_books = Book.objects.filter(stock__lte=5).order_by("stock")[:10]

    daily_sales = []
    for d in range(period_days):
        day = period_start + timedelta(days=d)
        day_qs = period_orders.filter(created_at__date=day)
        cnt = day_qs.count()
        rev = day_qs.aggregate(r=Sum("total_amount"))["r"] or 0
        daily_sales.append({"label": day.strftime("%b %d"), "orders": cnt, "revenue": float(rev)})

    monthly = []
    month_anchor = period_end.replace(day=1)
    for i in range(6, -1, -1):
        month_start = (month_anchor - timedelta(days=i * 32)).replace(day=1)
        next_month = (month_start + timedelta(days=32)).replace(day=1)
        month_end = next_month - timedelta(days=1)
        window_start = max(month_start, period_start)
        window_end = min(month_end, period_end)
        if window_start > window_end:
            rev = 0
        else:
            rev = all_orders.filter(created_at__date__gte=window_start, created_at__date__lte=window_end).aggregate(r=Sum("total_amount"))["r"] or 0
        monthly.append({"label": month_start.strftime("%b %Y"), "revenue": float(rev)})

    top_categories = list(
        OrderItem.objects
        .filter(order__created_at__date__gte=period_start, order__created_at__date__lte=period_end, book__categories_m2m__isnull=False)
        .values("book__categories_m2m__name")
        .annotate(
            units=Sum("quantity"),
            revenue=Sum(F("quantity") * F("price")),
        )
        .order_by("-revenue")[:8]
    )

    top_customers = (
        period_orders
        .values("customer__user__username", "customer__name")
        .annotate(total_spent=Sum("total_amount"), order_count=Count("id"))
        .order_by("-total_spent")[:8]
    )

    recent_orders = (
        period_orders.select_related("customer", "customer__user")
        .order_by("-created_at")[:8]
    )

    analytics_chart_data = {
        "daily": [{
            "label": d["label"],
            "orders": d["orders"],
            "revenue": float(d["revenue"]),
        } for d in daily_sales],
        "status": [{
            "label": s["status"],
            "count": s["count"],
        } for s in orders_by_status],
        "monthly": [{
            "label": m["label"],
            "revenue": float(m["revenue"]),
        } for m in monthly],
        "categories": [{
            "label": c.get("book__categories_m2m__name") or "Uncategorized",
            "revenue": float(c.get("revenue") or 0),
        } for c in top_categories],
        "top_books": [{
            "label": (b["book__title"] or "")[:22],
            "units": int(b["units_sold"] or 0),
            "revenue": float(b["revenue"] or 0),
        } for b in top_books],
        "top_customers": [{
            "name": c.get("customer__name") or c.get("customer__user__username") or "Unknown",
            "orders": int(c.get("order_count") or 0),
            "spent": float(c.get("total_spent") or 0),
        } for c in top_customers],
    }

    range_labels = {
        "7d": "Last 7 days",
        "30d": "Last 30 days",
        "90d": "Last 90 days",
        "custom": "Custom range",
    }

    return render(request, "staff/analytics.html", {
        "period_revenue": period_revenue,
        "period_order_count": period_order_count,
        "period_customer_count": period_customer_count,
        "avg_order_value": avg_order_value,
        "revenue_delta": revenue_delta,
        "orders_delta": orders_delta,
        "avg_delta": avg_delta,
        "total_books": total_books,
        "total_customers": total_customers,
        "inbox_unread_count": inbox_unread_count,
        "inbox_read_count": inbox_read_count,
        "top_books": top_books,
        "low_stock_books": low_stock_books,
        "top_customers": top_customers,
        "recent_orders": recent_orders,
        "analytics_chart_data": analytics_chart_data,
        "range_key": range_key,
        "range_label": range_labels.get(range_key, "Last 30 days"),
        "start_date": period_start.isoformat(),
        "end_date": period_end.isoformat(),
    })
