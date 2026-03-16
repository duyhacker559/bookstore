from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from store.models.order.order import Order
from store.models.order.payment import Payment
from store.models.order.shipping import Shipment
from store.models.customer.customer import Customer
from store.services.payment_shipping_service import PaymentService, ShippingService
from decimal import Decimal


@login_required
def payment_initiate(request, order_id):
    """Initiate payment for an order"""
    order = get_object_or_404(Order, id=order_id, customer__user=request.user)
    
    if request.method == 'GET':
        payment_methods = PaymentService.PAYMENT_METHODS
        return render(request, 'order/payment.html', {
            'order': order,
            'payment_methods': payment_methods
        })
    
    if request.method == 'POST':
        method = request.POST.get('method')
        
        # Create payment record
        payment = PaymentService.create_payment(order, method, order.total_amount)
        
        # For now, auto-approve (in production, integrate with actual gateway)
        if method == 'cod':
            # COD doesn't need immediate payment
            payment.status = 'Pending'
        else:
            # Simulate payment gateway approval
            payment = PaymentService.process_payment(payment, is_successful=True)
        
        payment.save()
        return redirect('payment_success', order_id=order.id)


@login_required
def payment_success(request, order_id):
    """Display payment success"""
    order = get_object_or_404(Order, id=order_id, customer__user=request.user)
    payment = get_object_or_404(Payment, order=order)
    
    return render(request, 'order/payment_success.html', {
        'order': order,
        'payment': payment
    })


@login_required
def payment_api(request, order_id):
    """API endpoint for payment processing"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    order = get_object_or_404(Order, id=order_id, customer__user=request.user)
    method = request.POST.get('method', 'credit_card')
    
    try:
        payment = PaymentService.create_payment(order, method, order.total_amount)
        # Simulate payment processing
        payment = PaymentService.process_payment(payment, is_successful=True)
        
        return JsonResponse({
            'status': 'success',
            'payment_id': payment.id,
            'message': 'Payment processed successfully'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)


@login_required
def shipping_select(request, order_id):
    """Select shipping method for an order"""
    order = get_object_or_404(Order, id=order_id, customer__user=request.user)
    
    if request.method == 'GET':
        shipping_options = ShippingService.get_shipping_options(weight=1.0)
        return render(request, 'order/shipping_select.html', {
            'order': order,
            'shipping_options': shipping_options
        })
    
    if request.method == 'POST':
        method = request.POST.get('method', 'standard')
        address = request.POST.get('address')
        
        if not address:
            return JsonResponse({'error': 'Address required'}, status=400)
        
        fee = ShippingService.calculate_shipping_fee(method)
        shipment = ShippingService.create_shipment(order, method, address, fee)
        
        # Update order with shipping fee
        order.total_amount += Decimal(str(fee))
        order.status = 'Awaiting Shipment'
        order.save()
        
        return redirect('shipping_success', order_id=order.id)


@login_required
def shipping_success(request, order_id):
    """Display shipping confirmation"""
    order = get_object_or_404(Order, id=order_id, customer__user=request.user)
    shipment = get_object_or_404(Shipment, order=order)
    
    return render(request, 'order/shipping_success.html', {
        'order': order,
        'shipment': shipment
    })


@login_required
def shipping_api(request, order_id):
    """API endpoint for shipping options and selection"""
    if request.method == 'GET':
        weight = request.GET.get('weight', 1.0)
        options = ShippingService.get_shipping_options(float(weight))
        return JsonResponse({'shipping_options': options})
    
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id, customer__user=request.user)
        method = request.POST.get('method', 'standard')
        address = request.POST.get('address')
        
        if not address:
            return JsonResponse({'error': 'Address required'}, status=400)
        
        try:
            fee = ShippingService.calculate_shipping_fee(method)
            shipment = ShippingService.create_shipment(order, method, address, fee)
            
            return JsonResponse({
                'status': 'success',
                'shipment_id': shipment.id,
                'fee': float(fee),
                'message': f'Shipment created with {ShippingService.SHIPPING_METHODS[method]["name"]}'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)


@login_required
def shipment_track(request, shipment_id):
    """Track a shipment"""
    shipment = get_object_or_404(Shipment, id=shipment_id, order__customer__user=request.user)
    
    return render(request, 'order/track_shipment.html', {
        'shipment': shipment,
        'order': shipment.order
    })


def shipment_track_api(request, shipment_id):
    """API endpoint to track shipment (public)"""
    shipment = get_object_or_404(Shipment, id=shipment_id)
    
    return JsonResponse({
        'shipment_id': shipment.id,
        'status': shipment.status,
        'address': shipment.address,
        'method': shipment.method_name,
        'fee': float(shipment.fee),
        'order_id': shipment.order.id
    })
