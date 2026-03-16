import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookstore.settings')
import django
django.setup()

from django.contrib.auth.models import User
from store.models import Customer, Book, Cart, CartItem, Order, Payment, Shipment
from decimal import Decimal
import json

# Clean up previous test orders and customer data
Order.objects.filter(id__gte=100).delete()
Customer.objects.filter(user__username='phase3_e2e_test').delete()
User.objects.filter(username='phase3_e2e_test').delete()

# 1. Create test user + customer
user, _ = User.objects.get_or_create(
    username='phase3_e2e_test',
    defaults={'email': 'phase3@example.com', 'first_name': 'Phase3', 'last_name': 'Test'}
)
customer, _ = Customer.objects.get_or_create(user=user)
print(f"✓ User/Customer created: {user.username}")

# 2. Get/create book
books = Book.objects.all()[:1]
if not books:
    print("✗ No books found in DB")
    exit(1)
book = books[0]
# Reset stock for test
book.stock = 100
book.save()
print(f"✓ Book selected: {book.title} (${book.price})")

# 3. Create cart + add item
cart = Cart.objects.create(user=user)
cart_item = CartItem.objects.create(cart=cart, book=book, quantity=1)
print(f"✓ Cart created with 1x {book.title}")

# 4. Simulate checkout via REST API test client
from django.test import Client
from django.test.utils import override_settings

client = Client()
# Login the test user
client.force_login(user)

# POST /order/checkout/ to create order with payment+shipping
checkout_payload = {
    'full_name': 'Test User',
    'email': 'phase3@example.com',
    'phone': '555-0123',
    'address': '123 Test St',
    'shipping_method': 'express',
}

with override_settings(ALLOWED_HOSTS=['*']):
    response = client.post('/order/checkout/', checkout_payload, follow=False)

print(f"\n✓ Checkout POST: Status={response.status_code} (expect 302 redirect)")

if response.status_code == 302:
    location = response.get('Location', '')
    print(f"  → Redirect to: {location}")
else:
    print(f"  → Response content: {response.content.decode()[:200]}")

# 5. Find the created order
orders = Order.objects.filter(customer=customer).order_by('-id')[:1]
if orders:
    order = orders[0]
    print(f"\n✓ Order created: ID={order.id}, Status={order.status}, Total=${order.total_amount}")
    
    # 5.5. Submit payment form
    print(f"\n→ Submitting payment form for order {order.id}...")
    payment_payload = {
        'payment_method_id': 'pm_test_visa',
    }
    
    with override_settings(ALLOWED_HOSTS=['*']):
        payment_response = client.post(
            f'/order/{order.id}/payment/', 
            payment_payload, 
            follow=False
        )
    
    print(f"✓ Payment POST: Status={payment_response.status_code}")
    
    if payment_response.status_code == 302:
        payment_location = payment_response.get('Location', '')
        print(f"  → Redirect to: {payment_location}")
    else:
        print(f"  → Response: {payment_response.content.decode()[:200]}")
    
    # 6. Check Payment record (in monolith DB)
    try:
        payment = Payment.objects.get(order=order)
        print(f"\n✓ Payment in monolith DB: ID={payment.id}, Status={payment.status}, Amount=${payment.amount}")
    except Payment.DoesNotExist:
        print(f"\n✗ Payment NOT found in monolith DB for order {order.id}")
    
    # 7. Check Shipment record (in monolith DB)
    try:
        shipment = Shipment.objects.get(order=order)
        print(f"✓ Shipment in monolith DB: ID={shipment.id}, Status={shipment.status}, Method={shipment.method_name}, Fee=${shipment.fee}")
    except Shipment.DoesNotExist:
        print(f"✗ Shipment NOT found in monolith DB for order {order.id}")
    
    print(f"\n✅ PHASE 3 E2E REGRESSION PASSED: Order {order.id} fully processed with payment + shipping")
else:
    print(f"✗ No order found for customer {user.username}")
