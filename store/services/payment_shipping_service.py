from decimal import Decimal
from store.models.order.payment import Payment
from store.models.order.shipping import Shipment


class PaymentService:
    """Handle payment processing logic"""
    
    PAYMENT_METHODS = {
        'credit_card': 'Credit Card',
        'debit_card': 'Debit Card',
        'wallet': 'Digital Wallet',
        'cod': 'Cash on Delivery'
    }
    
    @staticmethod
    def create_payment(order, method, amount):
        """Create a payment record for an order"""
        payment = Payment.objects.create(
            order=order,
            method_name=PaymentService.PAYMENT_METHODS.get(method, method),
            amount=amount,
            status='Pending'
        )
        return payment
    
    @staticmethod
    def process_payment(payment, is_successful=True):
        """Update payment status (simplified - no external gateway)"""
        payment.status = 'Completed' if is_successful else 'Failed'
        payment.save()
        
        # Update order status
        if is_successful:
            payment.order.status = 'Paid'
        else:
            payment.order.status = 'Payment Failed'
        payment.order.save()
        
        return payment
    
    @staticmethod
    def refund(payment):
        """Process a refund for a payment"""
        if payment.status != 'Completed':
            raise ValueError("Cannot refund a non-completed payment")
        payment.status = 'Refunded'
        payment.save()
        
        payment.order.status = 'Refunded'
        payment.order.save()
        return payment


class ShippingService:
    """Handle shipping and delivery logic"""
    
    SHIPPING_METHODS = {
        'standard': {'name': 'Standard Shipping', 'fee': Decimal('5.00'), 'days': 5},
        'express': {'name': 'Express Shipping', 'fee': Decimal('15.00'), 'days': 2},
        'overnight': {'name': 'Overnight Shipping', 'fee': Decimal('30.00'), 'days': 1},
    }
    
    @staticmethod
    def calculate_shipping_fee(method, weight=1.0):
        """Calculate shipping fee based on method and weight"""
        if method not in ShippingService.SHIPPING_METHODS:
            raise ValueError(f"Unknown shipping method: {method}")
        
        base_fee = ShippingService.SHIPPING_METHODS[method]['fee']
        # Simple weight-based calculation
        weight_fee = Decimal(str(weight)) * Decimal('1.5')
        return base_fee + weight_fee
    
    @staticmethod
    def create_shipment(order, method, address, fee):
        """Create a shipment record for an order"""
        shipment = Shipment.objects.create(
            order=order,
            address=address,
            status='Pending',
            method_name=ShippingService.SHIPPING_METHODS.get(method, {}).get('name', method),
            fee=fee
        )
        return shipment
    
    @staticmethod
    def update_shipment_status(shipment, status):
        """Update shipment status"""
        valid_statuses = ['Pending', 'Processing', 'Shipped', 'In Transit', 'Delivered', 'Failed']
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")
        
        shipment.status = status
        shipment.save()
        
        # Sync order status with shipment
        if status == 'Delivered':
            shipment.order.status = 'Delivered'
        elif status == 'Failed':
            shipment.order.status = 'Delivery Failed'
        else:
            shipment.order.status = status
        
        shipment.order.save()
        return shipment
    
    @staticmethod
    def get_shipping_options(weight=1.0):
        """Return available shipping options with calculated fees"""
        options = {}
        for key, details in ShippingService.SHIPPING_METHODS.items():
            fee = ShippingService.calculate_shipping_fee(key, weight)
            options[key] = {
                'name': details['name'],
                'fee': float(fee),
                'estimated_days': details['days']
            }
        return options
