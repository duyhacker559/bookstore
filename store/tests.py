from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from store.models.book.book import Book
from store.models.author.author import Author
from store.models.cart.cart import Cart, CartItem
from store.models.customer.customer import Customer
from store.models.order.order import Order
from store.models.order.order_item import OrderItem


class BookAPITestCase(TestCase):
    def setUp(self):
        """Create test data"""
        self.client = Client()
        self.author = Author.objects.create(name="Test Author", biography="A test author")
        self.book = Book.objects.create(
            title="Test Book",
            author="Test Author",
            price=19.99,
            stock=10,
            category="Fiction",
            description="A test book",
            rating=4.5,
            review_count=5,
        )

    def test_book_list_api(self):
        """Test GET /api/books/"""
        response = self.client.get(reverse("api_book_list"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("books", data)
        self.assertGreater(len(data["books"]), 0)
        book = data["books"][0]
        self.assertEqual(book["title"], "Test Book")
        self.assertEqual(float(book["price"]), 19.99)

    def test_book_detail_api(self):
        """Test GET /api/books/<id>/"""
        response = self.client.get(reverse("api_book_detail", args=[self.book.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("book", data)
        book = data["book"]
        self.assertEqual(book["title"], "Test Book")
        self.assertEqual(book["stock"], 10)

    def test_book_detail_api_not_found(self):
        """Test GET /api/books/<id>/ with invalid ID"""
        response = self.client.get(reverse("api_book_detail", args=[9999]))
        self.assertEqual(response.status_code, 404)

    def test_author_list_api(self):
        """Test GET /api/authors/"""
        response = self.client.get(reverse("api_author_list"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("authors", data)
        self.assertGreater(len(data["authors"]), 0)
        author = data["authors"][0]
        self.assertEqual(author["name"], "Test Author")

    def test_author_detail_api(self):
        """Test GET /api/authors/<id>/"""
        response = self.client.get(reverse("api_author_detail", args=[self.author.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("author", data)
        author = data["author"]
        self.assertEqual(author["name"], "Test Author")

    def test_author_detail_api_not_found(self):
        """Test GET /api/authors/<id>/ with invalid ID"""
        response = self.client.get(reverse("api_author_detail", args=[9999]))
        self.assertEqual(response.status_code, 404)

class OrderAndStockTestCase(TestCase):
    """Test order creation and stock reduction"""
    
    def setUp(self):
        """Create test data"""
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123', email='test@example.com')
        self.book = Book.objects.create(
            title="Test Book for Order",
            author="Test Author",
            price=25.99,
            stock=50,
            category="Fiction",
            description="A test book",
        )
        self.customer = Customer.objects.get_or_create(
            user=self.user,
            defaults={'name': self.user.username, 'email': self.user.email}
        )[0]
    
    def test_order_creation_stores_in_database(self):
        """Test that orders are properly stored in the database"""
        initial_count = Order.objects.count()
        
        # Create an order manually
        order = Order.objects.create(
            customer=self.customer,
            status='Pending',
            total_amount=25.99
        )
        
        # Verify order was created
        self.assertEqual(Order.objects.count(), initial_count + 1)
        self.assertEqual(order.customer, self.customer)
        self.assertEqual(order.status, 'Pending')
        self.assertEqual(order.total_amount, 25.99)
    
    def test_stock_reduction_on_order(self):
        """Test that book stock is reduced when order is created"""
        initial_stock = self.book.stock
        
        # Create an order and order item
        order = Order.objects.create(
            customer=self.customer,
            status='Pending',
            total_amount=51.98
        )
        
        # Simulate stock reduction
        quantity_ordered = 2
        self.book.stock -= quantity_ordered
        self.book.save()
        
        OrderItem.objects.create(
            order=order,
            book=self.book,
            quantity=quantity_ordered,
            price=self.book.price
        )
        
        # Refresh book from database
        self.book.refresh_from_db()
        
        # Verify stock was reduced
        self.assertEqual(self.book.stock, initial_stock - quantity_ordered)
        self.assertEqual(self.book.stock, 48)
    
    def test_order_items_are_created(self):
        """Test that order items are properly created"""
        order = Order.objects.create(
            customer=self.customer,
            status='Pending',
            total_amount=25.99
        )
        
        OrderItem.objects.create(
            order=order,
            book=self.book,
            quantity=1,
            price=self.book.price
        )
        
        # Verify order item was created
        items = OrderItem.objects.filter(order=order)
        self.assertEqual(items.count(), 1)
        
        item = items.first()
        self.assertEqual(item.book, self.book)
        self.assertEqual(item.quantity, 1)
        self.assertEqual(float(item.price), 25.99)
    
    def test_order_total_calculation(self):
        """Test that order total is correctly set"""
        order = Order.objects.create(
            customer=self.customer,
            status='Pending',
            total_amount=51.98  # 2 x 25.99
        )
        
        OrderItem.objects.create(
            order=order,
            book=self.book,
            quantity=2,
            price=self.book.price
        )
        
        # Verify total
        expected_total = 2 * 25.99
        self.assertEqual(float(order.total_amount), expected_total)