from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from store.models.cart.cart import Cart
from store.models.order.order import Order
from store.models.order.order_item import OrderItem
from store.models.customer.customer import Customer

@login_required(login_url='/login/')
def checkout(request):
    cart = Cart.objects.filter(user=request.user).first()
    if not cart or not cart.items.exists():
        return redirect("/cart/")

    # Create Order
    # Ensure customer profile exists
    customer, created = Customer.objects.get_or_create(user=request.user, defaults={'name': request.user.username, 'email': request.user.email})
    
    total_amount = sum(item.product.price * item.quantity for item in cart.items.all())
    
    order = Order.objects.create(
        customer=customer,
        total_amount=total_amount,
        status="Pending"
    )

    # Create Order Items and Clear Cart
    for item in cart.items.all():
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            price=item.product.price
        )
        item.product.stock -= item.quantity # Simple stock management
        item.product.save()
    
    # Clear Cart
    cart.items.all().delete()
    
    # Redirect to Payment or Success
    return render(request, "order/success.html", {"order": order})
