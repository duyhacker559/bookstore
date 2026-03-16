from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.contrib import messages
from store.models.book.book import Book
from store.models.cart.cart import Cart, CartItem
from store.models.customer.customer import Customer
from store.models.order.order import Order
from store.models.order.order_item import OrderItem
from store.models.order.payment import Payment
from store.models.order.shipping import Shipment
from store.services.payment_shipping_service import ShippingService, PaymentService
from store.payment_client import PaymentClient, PaymentServiceUnavailable, PaymentProcessingError
from store.shipping_client import ShippingClient, ShippingServiceUnavailable
from store.events import publish_event
from store.services.notification_service import create_user_notification
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)
payment_client = PaymentClient()
shipping_client = ShippingClient()


def _build_shipment_timeline(current_status):
    """Build timeline metadata for shipment tracking template rendering."""
    ordered_statuses = ['Pending', 'Processing', 'Shipped', 'In Transit', 'Delivered']
    current_index = 0

    if current_status in ordered_statuses:
        current_index = ordered_statuses.index(current_status)

    return [
        {
            'label': status,
            'is_current': idx == current_index,
            'is_completed': idx < current_index,
        }
        for idx, status in enumerate(ordered_statuses)
    ]


def _options_as_map(options_list):
    """Convert shipping option list from service into existing template-friendly map."""
    options_map = {}
    for option in options_list:
        code = option.get('code')
        if not code:
            continue
        options_map[code] = {
            'name': option.get('name', code),
            'fee': option.get('fee', 0),
            'estimated_days': option.get('estimated_days', 0),
        }
    return options_map


def _calculate_cart_totals(cart):
    """Return cart totals used by page and AJAX quantity updates."""
    items = cart.items.select_related('book')
    cart_total = sum(Decimal(str(item.book.price)) * item.quantity for item in items)
    tax = cart_total * Decimal('0.08')
    total = cart_total + tax
    return cart_total, tax, total, items.count()


def add_to_cart(request, book_id):
    """Add book to cart - redirect to login if not authenticated"""
    book = get_object_or_404(Book, id=book_id)
    
    if not request.user.is_authenticated:
        messages.info(request, 'Please log in to add items to cart')
        return redirect('customer_login')
    
    # Get quantity from POST data or query parameter, default to 1
    quantity = 1
    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', 1))
            quantity = max(1, min(quantity, book.stock))  # Ensure valid range
        except (ValueError, TypeError):
            quantity = 1
    else:
        try:
            quantity = int(request.GET.get('quantity', 1))
            quantity = max(1, min(quantity, book.stock))  # Ensure valid range
        except (ValueError, TypeError):
            quantity = 1
    
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, book=book)
    
    if book.stock <= 0:
        messages.error(request, f'"{book.title}" is currently out of stock.')
        return redirect('book_list')

    requested_quantity = cart_item.quantity + quantity if not created else quantity
    final_quantity = min(max(requested_quantity, 1), book.stock)
    cart_item.quantity = final_quantity
    cart_item.save()

    if final_quantity < requested_quantity:
        messages.warning(request, f'Only {book.stock} copy(ies) of "{book.title}" are in stock. Cart quantity adjusted.')
    else:
        messages.success(request, f'{quantity} copy(ies) of "{book.title}" added to cart!')
    return redirect('book_list')


def remove_from_cart(request, book_id):
    """Remove book from cart"""
    if not request.user.is_authenticated:
        return redirect('customer_login')
    
    cart = Cart.objects.filter(user=request.user).first()
    if cart:
        CartItem.objects.filter(cart=cart, book_id=book_id).delete()
        messages.success(request, 'Item removed from cart')
    
    return redirect('cart')


def cart_view(request):
    """Display shopping cart - can be viewed by guest"""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        items = cart.items.select_related("book").prefetch_related("book__images")
    else:
        items = []

    for item in items:
        cover = item.book.images.filter(is_cover=True).first() or item.book.images.first()
        item.book.cover_image = cover.image.url if cover and cover.image else ""
        item.total_price = Decimal(str(item.book.price)) * item.quantity
    
    if request.user.is_authenticated:
        cart_total, tax, total, _ = _calculate_cart_totals(cart)
    else:
        cart_total = Decimal('0.00')
        tax = Decimal('0.00')
        total = Decimal('0.00')
    
    return render(request, 'cart/cart_improved.html', {
        'items': items,
        'cart_total': cart_total,
        'tax': tax,
        'total': total,
    })


@login_required(login_url='customer_login')
def update_cart_quantity(request, book_id):
    """Update cart item quantity with stock validation."""
    is_ajax = (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
    )

    def _json_error(message, status=400):
        return JsonResponse({'success': False, 'message': message}, status=status)

    if request.method != 'POST':
        if is_ajax:
            return _json_error('Invalid request method.', status=405)
        return redirect('cart')

    cart = Cart.objects.filter(user=request.user).first()
    if not cart:
        if is_ajax:
            return _json_error('Cart not found.', status=404)
        messages.error(request, 'Cart not found.')
        return redirect('cart')

    cart_item = CartItem.objects.filter(cart=cart, book_id=book_id).select_related('book').first()
    if not cart_item:
        if is_ajax:
            return _json_error('Cart item not found.', status=404)
        messages.error(request, 'Cart item not found.')
        return redirect('cart')

    action = (request.POST.get('action') or '').strip().lower()
    requested_quantity = request.POST.get('quantity')

    try:
        requested_quantity = int(requested_quantity) if requested_quantity is not None else cart_item.quantity
    except (TypeError, ValueError):
        requested_quantity = cart_item.quantity

    if action == 'increase':
        requested_quantity = cart_item.quantity + 1
    elif action == 'decrease':
        requested_quantity = cart_item.quantity - 1

    if requested_quantity <= 0:
        book_title = cart_item.book.title
        cart_item.delete()
        cart_total, tax, total, item_count = _calculate_cart_totals(cart)

        if is_ajax:
            return JsonResponse({
                'success': True,
                'removed': True,
                'message': f'"{book_title}" removed from cart.',
                'cart_total': f'{cart_total:.2f}',
                'tax': f'{tax:.2f}',
                'total': f'{total:.2f}',
                'item_count': item_count,
            })

        messages.success(request, f'"{book_title}" removed from cart.')
        return redirect('cart')

    available_stock = max(cart_item.book.stock, 0)
    if available_stock <= 0:
        book_title = cart_item.book.title
        cart_item.delete()
        cart_total, tax, total, item_count = _calculate_cart_totals(cart)

        if is_ajax:
            return JsonResponse({
                'success': True,
                'removed': True,
                'message': f'"{book_title}" is out of stock and was removed from your cart.',
                'cart_total': f'{cart_total:.2f}',
                'tax': f'{tax:.2f}',
                'total': f'{total:.2f}',
                'item_count': item_count,
            })

        messages.warning(request, f'"{cart_item.book.title}" is out of stock and was removed from your cart.')
        return redirect('cart')

    final_quantity = min(requested_quantity, available_stock)
    cart_item.quantity = final_quantity
    cart_item.save(update_fields=['quantity'])

    cart_total, tax, total, item_count = _calculate_cart_totals(cart)

    if final_quantity < requested_quantity:
        if is_ajax:
            return JsonResponse({
                'success': True,
                'removed': False,
                'message': f'Only {available_stock} copy(ies) of "{cart_item.book.title}" are available.',
                'quantity': final_quantity,
                'stock': available_stock,
                'line_total': f'{(Decimal(str(cart_item.book.price)) * final_quantity):.2f}',
                'cart_total': f'{cart_total:.2f}',
                'tax': f'{tax:.2f}',
                'total': f'{total:.2f}',
                'item_count': item_count,
            })
        messages.warning(request, f'Only {available_stock} copy(ies) of "{cart_item.book.title}" are available.')
    elif is_ajax:
        return JsonResponse({
            'success': True,
            'removed': False,
            'message': 'Quantity updated.',
            'quantity': final_quantity,
            'stock': available_stock,
            'line_total': f'{(Decimal(str(cart_item.book.price)) * final_quantity):.2f}',
            'cart_total': f'{cart_total:.2f}',
            'tax': f'{tax:.2f}',
            'total': f'{total:.2f}',
            'item_count': item_count,
        })

    return redirect('cart')


@login_required(login_url='customer_login')
def checkout(request):
    """Checkout page - requires login"""
    cart = Cart.objects.filter(user=request.user).first()
    
    if not cart or not cart.items.exists():
        messages.error(request, 'Your cart is empty')
        return redirect('book_list')
    
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '')
        email = request.POST.get('email', '')
        phone = request.POST.get('phone', '')
        address = request.POST.get('address', '')
        shipping_method = request.POST.get('shipping_method', 'standard')
        
        if not all([full_name, email, address]):
            messages.error(request, 'Please fill in all required fields')
            return redirect('checkout')
        
        # Create customer if doesn't exist
        customer, _ = Customer.objects.get_or_create(
            user=request.user,
            defaults={
                'name': full_name,
                'email': email,
                'phone': phone,
                'address': address
            }
        )
        
        # Calculate totals
        cart_items = cart.items.all()
        subtotal = sum(Decimal(str(item.book.price)) * item.quantity for item in cart_items)
        tax = subtotal * Decimal('0.08')

        # Calculate shipping fee (prefer external Shipping Service)
        shipping_fee = None
        try:
            service_options = shipping_client.get_shipping_options(weight=1.0)
            service_options_map = _options_as_map(service_options)
            selected = service_options_map.get(shipping_method)
            if selected:
                shipping_fee = Decimal(str(selected['fee']))
        except ShippingServiceUnavailable as exc:
            logger.warning("Shipping Service unavailable during fee calculation: %s", exc)

        if shipping_fee is None:
            shipping_fee = ShippingService.calculate_shipping_fee(shipping_method)

        total = subtotal + tax + shipping_fee
        
        # Create order
        order = Order.objects.create(
            customer=customer,
            status='Pending',
            total_amount=total
        )

        create_user_notification(
            customer,
            title=f"Order #{order.id} Created",
            message="Your order was created successfully. Complete payment to confirm it.",
            notification_type="order",
            link=f"/order/{order.id}/success/",
        )
        
        # Create order items and reduce stock
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                book=item.book,
                quantity=item.quantity,
                price=item.book.price
            )
            # Reduce book stock by ordered quantity
            item.book.stock -= item.quantity
            item.book.save()
        
        # Create shipment in external Shipping Service (and mirror locally)
        shipment_method_name = ShippingService.SHIPPING_METHODS.get(shipping_method, {}).get('name', shipping_method)
        try:
            shipping_result = shipping_client.create_shipment(
                order_id=str(order.id),
                address=address,
                method_code=shipping_method,
                fee=float(shipping_fee),
            )
            shipment_method_name = shipping_result.get('method_name', shipment_method_name)
            publish_event('shipment.created', {
                'order_id': order.id,
                'shipping_method': shipping_method,
                'method_name': shipment_method_name,
                'fee': float(shipping_fee),
            })
        except (ShippingServiceUnavailable, Exception) as exc:
            logger.warning("Shipping Service create failed, falling back to local shipment: %s", exc)

        # Keep a local shipment record for existing pages/workflows
        shipment = Shipment.objects.create(
            order=order,
            address=address,
            status='Pending',
            method_name=shipment_method_name,
            fee=float(shipping_fee),
        )

        create_user_notification(
            customer,
            title=f"Shipment Created for Order #{order.id}",
            message=f"Shipment was created with {shipment_method_name}. You can track updates anytime.",
            notification_type="shipping",
            link=f"/order/{order.id}/track/",
        )
        
        # Store order and shipment in session for next step
        request.session['order_id'] = order.id
        request.session['shipment_id'] = shipment.id
        
        messages.success(request, 'Order created! Proceed to payment.')
        return redirect('payment_initiate', order_id=order.id)
    
    # GET request - show checkout form
    items = cart.items.all()
    subtotal = sum(Decimal(str(item.book.price)) * item.quantity for item in items)
    tax = subtotal * Decimal('0.08')
    total = subtotal + tax
    
    try:
        service_options = shipping_client.get_shipping_options(weight=1.0)
        shipping_options = _options_as_map(service_options)
    except ShippingServiceUnavailable as exc:
        logger.warning("Shipping Service unavailable for checkout options: %s", exc)
        shipping_options = ShippingService.get_shipping_options(weight=1.0)

    return render(request, 'order/checkout_improved.html', {
        'cart_items': items,
        'subtotal': subtotal,
        'tax': tax,
        'total': total,
        'shipping_options': shipping_options,
    })


@login_required(login_url='customer_login')
def payment_confirm(request, order_id):
    """Process payment and show confirmation"""
    order = get_object_or_404(Order, id=order_id)
    
    # Verify customer owns this order
    if order.customer.user != request.user:
        messages.error(request, 'Unauthorized access')
        return redirect('book_list')
    
    if request.method == 'POST':
        payment_method_id = request.POST.get('method', '')  # Changed from 'payment_method_id' to 'method' to match form field
        
        if not payment_method_id:
            messages.error(request, 'Payment method is required')
            return redirect('payment_initiate', order_id=order_id)
        try:
            # Call external Payment Service
            logger.info(f"Calling Payment Service for order {order.id}")
            
            # Ensure valid email for payment service (required field with strict validation)
            customer_email = order.customer.email or request.user.email or ''
            customer_email = customer_email.strip()
            
            if not customer_email or '@' not in customer_email or customer_email.endswith('.local'):
                # Generate valid email for users without email configured
                # Use example.com which passes strict validation (designated for documentation)
                customer_email = f"{request.user.username}@example.com"
            
            logger.info(f"Processing payment for order {order.id} with email: {customer_email}")
            
            payment_result = payment_client.process_payment(
                order_id=str(order.id),
                amount=float(order.total_amount),
                customer_email=customer_email,
                payment_method_id=payment_method_id,
                currency='USD'
            )
            
            if payment_result['status'] == 'succeeded':
                # Create payment record in monolith
                payment = Payment.objects.create(
                    order=order,
                    method_name='External Payment Service',
                    amount=Decimal(str(payment_result['amount'])),
                    status='completed'
                )
                
                # Update order status
                order.status = 'Confirmed'
                order.save()
                
                # Publish order paid event
                publish_event('order.paid', {
                    'order_id': order.id,
                    'payment_id': payment.id,
                    'transaction_id': payment_result['payment_id'],
                    'amount': float(order.total_amount),
                })

                create_user_notification(
                    order.customer,
                    title=f"Payment Successful for Order #{order.id}",
                    message="Payment completed and your order is now confirmed.",
                    notification_type="payment",
                    link=f"/order/{order.id}/success/",
                )
                
                # Clear cart after successful payment
                cart = Cart.objects.filter(user=request.user).first()
                if cart:
                    cart.items.all().delete()
                
                messages.success(request, 'Payment successful! Your order is confirmed.')
                logger.info(f"Payment succeeded for order {order.id}")
                
                return redirect('order_success', order_id=order.id)
            else:
                messages.error(request, f"Payment failed: {payment_result.get('message', 'Unknown error')}")
                create_user_notification(
                    order.customer,
                    title=f"Payment Failed for Order #{order.id}",
                    message=payment_result.get('message', 'Payment could not be completed. Please try again.'),
                    notification_type="payment",
                    link=f"/order/{order.id}/payment/",
                )
                logger.warning(f"Payment failed for order {order.id}: {payment_result}")
                return redirect('payment_initiate', order_id=order_id)
                
        except PaymentProcessingError as e:
            messages.error(request, f'Payment declined: {str(e)}')
            create_user_notification(
                order.customer,
                title=f"Payment Declined for Order #{order.id}",
                message=str(e),
                notification_type="payment",
                link=f"/order/{order.id}/payment/",
            )
            logger.error(f"Payment processing error for order {order.id}: {e}")
            return redirect('payment_initiate', order_id=order_id)
            
        except PaymentServiceUnavailable as e:
            messages.error(request, f'Payment service unavailable: {str(e)} Please try again later.')
            create_user_notification(
                order.customer,
                title=f"Payment Service Unavailable for Order #{order.id}",
                message="Payment service is temporarily unavailable. Please try again later.",
                notification_type="payment",
                link=f"/order/{order.id}/payment/",
            )
            logger.error(f"Payment service error for order {order.id}: {e}")
            return redirect('payment_initiate', order_id=order_id)
            
        except Exception as e:
            messages.error(request, 'An error occurred while processing your payment. Please try again.')
            create_user_notification(
                order.customer,
                title=f"Payment Error for Order #{order.id}",
                message="An unexpected payment error occurred. Please try again.",
                notification_type="payment",
                link=f"/order/{order.id}/payment/",
            )
            logger.exception(f"Unexpected error processing payment for order {order.id}: {e}")
            return redirect('payment_initiate', order_id=order_id)
    
    # GET request - show payment options
    shipping_options = ShippingService.get_shipping_options()
    payment_methods = PaymentService.PAYMENT_METHODS
    
    return render(request, 'order/payment_improved.html', {
        'order': order,
        'payment_methods': payment_methods,
        'shipping_options': shipping_options,
    })


@login_required(login_url='customer_login')
def order_success(request, order_id):
    """Order confirmation page"""
    order = get_object_or_404(Order, id=order_id)
    
    # Verify customer owns this order
    if order.customer.user != request.user:
        messages.error(request, 'Unauthorized access')
        return redirect('book_list')
    
    payment = Payment.objects.filter(order=order).first()
    shipment = Shipment.objects.filter(order=order).first()

    order_items = order.items.select_related('book').prefetch_related('book__images')
    subtotal = Decimal('0.00')
    total_units = 0

    for item in order_items:
        cover = item.book.images.filter(is_cover=True).first() or item.book.images.first()
        item.book.cover_image = cover.image.url if cover and cover.image else ''
        item.line_total = Decimal(str(item.price)) * item.quantity
        subtotal += item.line_total
        total_units += item.quantity

    shipping_fee = Decimal(str(shipment.fee)) if shipment and shipment.fee is not None else Decimal('0.00')
    tax_amount = max(Decimal(str(order.total_amount)) - subtotal - shipping_fee, Decimal('0.00'))
    
    return render(request, 'order/success_improved.html', {
        'order': order,
        'payment': payment,
        'shipment': shipment,
        'order_items': order_items,
        'subtotal': subtotal,
        'shipping_fee': shipping_fee,
        'tax_amount': tax_amount,
        'total_units': total_units,
    })


def track_shipment(request, shipment_id):
    """Track shipment - can be public or private depending on auth"""
    shipment = get_object_or_404(Shipment, id=shipment_id)
    timeline = _build_shipment_timeline(shipment.status)
    
    # If user is authenticated, verify they own this shipment
    if request.user.is_authenticated:
        if shipment.order.customer.user != request.user:
            messages.error(request, 'Unauthorized access')
            return redirect('book_list')
    
    return render(request, 'order/track_shipment_improved.html', {
        'shipment': shipment,
        'timeline': timeline,
    })


def track_order(request, order_id):
    """Track shipment by order id to avoid exposing shipment ids in URLs."""
    order = get_object_or_404(Order, id=order_id)
    shipment = get_object_or_404(Shipment, order=order)
    timeline = _build_shipment_timeline(shipment.status)

    # If user is authenticated, verify they own this order
    if request.user.is_authenticated:
        if order.customer.user != request.user:
            messages.error(request, 'Unauthorized access')
            return redirect('book_list')

    return render(request, 'order/track_shipment_improved.html', {
        'shipment': shipment,
        'timeline': timeline,
    })
