from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from store.models.book.book import Book
from store.models.cart.cart import Cart, CartItem

@login_required(login_url='/login/')
def add_to_cart(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    # Check if item exists
    cart_item, created = CartItem.objects.get_or_create(cart=cart, book=book)
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    
    return redirect("/cart/")

@login_required(login_url='/login/')
def remove_from_cart(request, book_id):
    cart = Cart.objects.filter(user=request.user).first()
    if cart:
        CartItem.objects.filter(cart=cart, book_id=book_id).delete()
    return redirect("/cart/")

@login_required(login_url='/login/')
def cart_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    items = cart.items.all()
    total = sum(item.book.price * item.quantity for item in items)

    return render(request, "cart/cart.html", {
        "cart": items,
        "total": total
    })
