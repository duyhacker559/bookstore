from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from store.models.customer.customer import Customer
from store.models.order.order import Order
from store.models.order.order_item import OrderItem
from store.models.book.book import Book
from datetime import datetime, timedelta


class OrdersPaginationAndFilterTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='pager', password='testpass')
        self.customer = Customer.objects.create(user=self.user, name='Pager', email='pager@test.com')

        # create a sample book
        self.book = Book.objects.create(title='PBook', author='Auth', price=10.0, stock=100)

        # create 25 orders with varying statuses and dates
        statuses = ['Pending', 'Processing', 'Confirmed', 'Delivered']
        today = datetime.utcnow()
        self.orders = []
        for i in range(25):
            status = statuses[i % len(statuses)]
            order = Order.objects.create(customer=self.customer, status=status, total_amount=10.0 * (i+1))
            # set created_at back i days for date filtering
            order.created_at = today - timedelta(days=i)
            order.save(update_fields=['created_at'])
            # add one item
            OrderItem.objects.create(order=order, book=self.book, quantity=1, price=self.book.price)
            self.orders.append(order)

    def test_pagination_page_size(self):
        self.client.login(username='pager', password='testpass')
        url = reverse('customer_home')
        response = self.client.get(url + '?page_size=20')
        self.assertEqual(response.status_code, 200)
        orders_page = response.context['orders_page']
        self.assertEqual(orders_page.paginator.per_page, 20)
        # ensure page has at most 20 entries
        self.assertLessEqual(len(orders_page.object_list), 20)

    def test_filter_status(self):
        self.client.login(username='pager', password='testpass')
        url = reverse('customer_home')
        response = self.client.get(url + '?status=Delivered&page_size=50')
        self.assertEqual(response.status_code, 200)
        orders_page = response.context['orders_page']
        # Count delivered in DB
        delivered_count = Order.objects.filter(customer=self.customer, status__iexact='Delivered').count()
        self.assertEqual(orders_page.paginator.count, delivered_count)

    def test_date_filter(self):
        self.client.login(username='pager', password='testpass')
        url = reverse('customer_home')
        start_date = (datetime.utcnow() - timedelta(days=5)).date().isoformat()
        response = self.client.get(url + f'?start_date={start_date}&page_size=50')
        self.assertEqual(response.status_code, 200)
        orders_page = response.context['orders_page']
        # All returned orders should have created_at >= start_date
        for o in orders_page.object_list:
            self.assertGreaterEqual(o.created_at.date(), datetime.strptime(start_date, '%Y-%m-%d').date())

    def test_base_query_preserved(self):
        self.client.login(username='pager', password='testpass')
        url = reverse('customer_home')
        response = self.client.get(url + '?status=Pending&page_size=10')
        self.assertEqual(response.status_code, 200)
        base_query = response.context.get('base_query', '')
        self.assertIn('status=Pending', base_query)
        self.assertIn('page_size=10', base_query)
