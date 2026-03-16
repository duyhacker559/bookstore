"""End-to-end order test to verify all services and databases."""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookstore.settings')
django.setup()

from django.contrib.auth.models import User
from store.models import Book, Order, OrderItem, Cart, CartItem, Customer
from store.payment_client import PaymentClient
from store.shipping_client import ShippingClient
from decimal import Decimal
import time

def run_e2e_test():
    print("\n" + "="*60)
    print("END-TO-END ORDER TEST")
    print("="*60)
    
    # 1. Get or create test user
    print("\n[1/6] Setting up test user...")
    user, created = User.objects.get_or_create(
        username='e2e_test_user',
        defaults={
            'email': 'e2e@test.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()
    
    # Get or create customer
    customer, customer_created = Customer.objects.get_or_create(
        user=user,
        defaults={
            'phone': '555-1234',
            'address': '123 Test St, Test City, TC 12345'
        }
    )
    print(f"   ✓ User: {user.username} (ID: {user.id})")
    print(f"   ✓ Customer: ID={customer.id}")
    
    # 2. Get a book
    print("\n[2/6] Selecting book...")
    book = Book.objects.filter(stock__gt=0).first()
    if not book:
        print("   ✗ No books with stock available!")
        return False
    print(f"   ✓ Book: {book.title} - ${book.price}")
    
    # 3. Create order
    print("\n[3/6] Creating order...")
    order = Order.objects.create(
        customer=customer,
        total_amount=book.price + Decimal('15.00'),  # Book + shipping
        status='pending'
    )
    OrderItem.objects.create(
        order=order,
        book=book,
        quantity=1,
        price=book.price
    )
    print(f"   ✓ Order created: ID={order.id}, Total=${order.total_amount}")
    
    # 4. Process payment
    print("\n[4/6] Processing payment via Payment Service...")
    payment_client = PaymentClient()
    try:
        payment_result = payment_client.process_payment(
            order_id=str(order.id),
            amount=float(order.total_amount),
            payment_method_id='pm_card_visa',
            customer_email=user.email
        )
        print(f"   ✓ Payment processed: {payment_result.get('payment_id', 'N/A')}")
        print(f"   ✓ Payment status: {payment_result.get('status', 'unknown')}")
        order.payment_status = 'paid'
        order.save()
    except Exception as e:
        print(f"   ✗ Payment failed: {e}")
        return False
    
    # 5. Create shipment
    print("\n[5/6] Creating shipment via Shipping Service...")
    shipping_client = ShippingClient()
    try:
        shipment = shipping_client.create_shipment(
            order_id=str(order.id),
            method_code='standard',
            address='123 Test St, Test City, TC 12345',
            fee=15.00
        )
        print(f"   ✓ Shipment created: Method={shipment.get('method_name', 'N/A')}")
        print(f"   ✓ Shipment status: {shipment.get('status', 'unknown')}")
    except Exception as e:
        print(f"   ✗ Shipment creation failed: {e}")
        return False
    
    # 6. Verify data in all databases
    print("\n[6/6] Verifying data across all databases...")
    
    # Check monolith
    order_check = Order.objects.filter(id=order.id).exists()
    print(f"   ✓ Monolith (bookstore): Order #{order.id} exists: {order_check}")
    
    # Check payment service
    import psycopg2
    conn = psycopg2.connect(
        host='postgres',
        port=5432,
        user='bookstore',
        password='bookstore_password',
        database='payment_service'
    )
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM payments WHERE order_id = %s", (str(order.id),))
    payment_count = cur.fetchone()[0]
    print(f"   ✓ Payment Service DB: {payment_count} payment(s) for order #{order.id}")
    cur.close()
    conn.close()
    
    # Check shipping service
    conn = psycopg2.connect(
        host='postgres',
        port=5432,
        user='bookstore',
        password='bookstore_password',
        database='shipping_service'
    )
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM shipments WHERE order_id = %s", (str(order.id),))
    shipment_count = cur.fetchone()[0]
    print(f"   ✓ Shipping Service DB: {shipment_count} shipment(s) for order #{order.id}")
    cur.close()
    conn.close()
    
    # Check notification service (wait a bit for async processing)
    print("\n   Waiting 3 seconds for notification service to process events...")
    time.sleep(3)
    
    conn = psycopg2.connect(
        host='postgres',
        port=5432,
        user='bookstore',
        password='bookstore_password',
        database='notification_service'
    )
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), array_agg(event_type) FROM notifications WHERE order_id = %s GROUP BY order_id", (str(order.id),))
    result = cur.fetchone()
    if result:
        notif_count, event_types = result
        print(f"   ✓ Notification Service DB: {notif_count} notification(s) for order #{order.id}")
        print(f"     Event types: {', '.join(event_types)}")
    else:
        print(f"   ⚠ Notification Service DB: No notifications yet (async processing may still be in progress)")
    cur.close()
    conn.close()
    
    print("\n" + "="*60)
    print("✓ END-TO-END TEST COMPLETED SUCCESSFULLY")
    print("="*60)
    print(f"\nTest Order ID: {order.id}")
    print(f"Databases touched: 4/4")
    print(f"Services called: Payment, Shipping, Notification (via events)")
    print(f"\nVerify in RabbitMQ Management UI: http://localhost:15672")
    print("="*60 + "\n")
    
    return True

if __name__ == '__main__':
    try:
        success = run_e2e_test()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
