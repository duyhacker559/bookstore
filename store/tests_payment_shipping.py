from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from store.models.customer.customer import Customer
from store.models.book.book import Book
from store.models.order.order import Order
from store.models.order.order_item import OrderItem
from store.models.order.payment import Payment
from store.models.order.shipping import Shipment
from store.services.payment_shipping_service import PaymentService, ShippingService


class PaymentServiceTestCase(TestCase):
    def setUp(self):
        """Create test data"""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.customer = Customer.objects.create(user=self.user, name='Test Customer', email='test@test.com')
        self.book = Book.objects.create(title='Test Book', author='Test Author', price=19.99, stock=10)
        self.order = Order.objects.create(customer=self.customer, status='Pending', total_amount=Decimal('19.99'))

    def test_create_payment_credit_card(self):
        """Test creating a payment with credit card"""
        payment = PaymentService.create_payment(self.order, 'credit_card', Decimal('19.99'))
        
        self.assertIsNotNone(payment.id)
        self.assertEqual(payment.method_name, 'Credit Card')
        self.assertEqual(payment.amount, Decimal('19.99'))
        self.assertEqual(payment.status, 'Pending')

    def test_create_payment_cod(self):
        """Test creating a payment with cash on delivery"""
        payment = PaymentService.create_payment(self.order, 'cod', Decimal('19.99'))
        
        self.assertEqual(payment.method_name, 'Cash on Delivery')
        self.assertEqual(payment.status, 'Pending')

    def test_process_payment_success(self):
        """Test processing a successful payment"""
        payment = PaymentService.create_payment(self.order, 'credit_card', Decimal('19.99'))
        payment = PaymentService.process_payment(payment, is_successful=True)
        
        self.assertEqual(payment.status, 'Completed')
        self.assertEqual(payment.order.status, 'Paid')

    def test_process_payment_failure(self):
        """Test processing a failed payment"""
        payment = PaymentService.create_payment(self.order, 'credit_card', Decimal('19.99'))
        payment = PaymentService.process_payment(payment, is_successful=False)
        
        self.assertEqual(payment.status, 'Failed')
        self.assertEqual(payment.order.status, 'Payment Failed')

    def test_refund_payment(self):
        """Test refunding a completed payment"""
        payment = PaymentService.create_payment(self.order, 'credit_card', Decimal('19.99'))
        payment = PaymentService.process_payment(payment, is_successful=True)
        payment = PaymentService.refund(payment)
        
        self.assertEqual(payment.status, 'Refunded')
        self.assertEqual(payment.order.status, 'Refunded')

    def test_refund_non_completed_payment(self):
        """Test that refunding a pending payment raises an error"""
        payment = PaymentService.create_payment(self.order, 'credit_card', Decimal('19.99'))
        
        with self.assertRaises(ValueError):
            PaymentService.refund(payment)


class ShippingServiceTestCase(TestCase):
    def setUp(self):
        """Create test data"""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.customer = Customer.objects.create(user=self.user, name='Test Customer', email='test@test.com')
        self.book = Book.objects.create(title='Test Book', author='Test Author', price=19.99, stock=10)
        self.order = Order.objects.create(customer=self.customer, status='Pending', total_amount=Decimal('19.99'))

    def test_get_shipping_options(self):
        """Test getting available shipping options"""
        options = ShippingService.get_shipping_options(weight=1.0)
        
        self.assertIn('standard', options)
        self.assertIn('express', options)
        self.assertIn('overnight', options)
        
        self.assertIn('name', options['standard'])
        self.assertIn('fee', options['standard'])
        self.assertIn('estimated_days', options['standard'])

    def test_calculate_shipping_fee_standard(self):
        """Test calculating standard shipping fee"""
        fee = ShippingService.calculate_shipping_fee('standard', weight=1.0)
        
        expected_fee = Decimal('5.00') + Decimal('1.5')
        self.assertEqual(fee, expected_fee)

    def test_calculate_shipping_fee_express(self):
        """Test calculating express shipping fee"""
        fee = ShippingService.calculate_shipping_fee('express', weight=1.0)
        
        expected_fee = Decimal('15.00') + Decimal('1.5')
        self.assertEqual(fee, expected_fee)

    def test_calculate_shipping_fee_invalid_method(self):
        """Test that invalid shipping method raises error"""
        with self.assertRaises(ValueError):
            ShippingService.calculate_shipping_fee('invalid_method')

    def test_create_shipment(self):
        """Test creating a shipment"""
        fee = ShippingService.calculate_shipping_fee('standard')
        shipment = ShippingService.create_shipment(
            self.order, 'standard', '123 Main St, City, State', fee
        )
        
        self.assertIsNotNone(shipment.id)
        self.assertEqual(shipment.status, 'Pending')
        self.assertEqual(shipment.method_name, 'Standard Shipping')
        self.assertEqual(shipment.address, '123 Main St, City, State')

    def test_update_shipment_status(self):
        """Test updating shipment status"""
        fee = ShippingService.calculate_shipping_fee('standard')
        shipment = ShippingService.create_shipment(
            self.order, 'standard', '123 Main St, City, State', fee
        )
        
        shipment = ShippingService.update_shipment_status(shipment, 'Shipped')
        self.assertEqual(shipment.status, 'Shipped')
        self.assertEqual(shipment.order.status, 'Shipped')

    def test_update_shipment_status_delivered(self):
        """Test updating shipment status to delivered"""
        fee = ShippingService.calculate_shipping_fee('standard')
        shipment = ShippingService.create_shipment(
            self.order, 'standard', '123 Main St, City, State', fee
        )
        
        shipment = ShippingService.update_shipment_status(shipment, 'Delivered')
        self.assertEqual(shipment.status, 'Delivered')
        self.assertEqual(shipment.order.status, 'Delivered')

    def test_update_shipment_status_invalid(self):
        """Test that invalid status raises error"""
        fee = ShippingService.calculate_shipping_fee('standard')
        shipment = ShippingService.create_shipment(
            self.order, 'standard', '123 Main St, City, State', fee
        )
        
        with self.assertRaises(ValueError):
            ShippingService.update_shipment_status(shipment, 'InvalidStatus')
