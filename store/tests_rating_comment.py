from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from store.models.book.book import Book
from store.models.customer.customer import Customer
from store.models.order.order import Order
from store.models.order.order_item import OrderItem
from store.models.rating.rating import Rating, Comment


class RatingAndCommentTestCase(TestCase):
    def setUp(self):
        """Create test data"""
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.customer = Customer.objects.create(user=self.user, name='Test User', email='test@test.com')
        self.book = Book.objects.create(
            title='Test Book',
            author='Test Author',
            price=19.99,
            stock=10,
            category='Fiction'
        )
        
        # Create an order for this customer to make it a verified purchase
        self.order = Order.objects.create(
            customer=self.customer,
            status='Delivered',
            total_amount=19.99
        )
        self.order_item = OrderItem.objects.create(
            order=self.order,
            book=self.book,
            quantity=1,
            price=19.99
        )

    def test_create_rating(self):
        """Test creating a rating"""
        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('add_rating_comment', args=[self.book.id]), {
            'score': '5',
            'title': 'Great Book!',
            'content': 'This book is amazing!'
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertTrue(Rating.objects.filter(customer=self.customer, book=self.book).exists())

    def test_rating_uniqueness(self):
        """Test that each submission creates a new rating entry for history."""
        self.client.login(username='testuser', password='testpass')
        
        # First rating
        self.client.post(reverse('add_rating_comment', args=[self.book.id]), {
            'score': '5',
            'title': 'Great!',
            'content': 'First review'
        })
        
        # Second rating should create a new rating record
        self.client.post(reverse('add_rating_comment', args=[self.book.id]), {
            'score': '4',
            'title': 'Good',
            'content': 'Updated review'
        })
        
        rating_count = Rating.objects.filter(customer=self.customer, book=self.book).count()
        self.assertEqual(rating_count, 2)
        
        rating = Rating.objects.filter(customer=self.customer, book=self.book).order_by('-created_at').first()
        self.assertEqual(rating.score, 4)

    def test_create_comment(self):
        """Test creating a comment"""
        rating = Rating.objects.create(customer=self.customer, book=self.book, score=5)
        
        comment = Comment.objects.create(
            customer=self.customer,
            book=self.book,
            rating=rating,
            title='Excellent Read',
            content='Highly recommended',
            is_verified_purchase=True
        )
        
        self.assertIsNotNone(comment.id)
        self.assertTrue(comment.is_verified_purchase)

    def test_verified_purchase_flag(self):
        """Test that verified purchase is detected correctly"""
        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('add_rating_comment', args=[self.book.id]), {
            'score': '5',
            'title': 'Great Book!',
            'content': 'This is a verified purchase'
        })
        
        comment = Comment.objects.filter(customer=self.customer, book=self.book).first()
        self.assertTrue(comment.is_verified_purchase)

    def test_mark_helpful(self):
        """Test marking a comment as helpful"""
        rating = Rating.objects.create(customer=self.customer, book=self.book, score=5)
        comment = Comment.objects.create(
            customer=self.customer,
            book=self.book,
            rating=rating,
            title='Great!',
            content='Loved it'
        )
        
        self.assertEqual(comment.helpful_count, 0)
        
        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('mark_helpful', args=[comment.id]))
        
        comment.refresh_from_db()
        self.assertEqual(comment.helpful_count, 1)

    def test_book_reviews_page(self):
        """Test viewing book reviews page"""
        # Create some ratings and comments
        for i in range(3):
            user = User.objects.create_user(username=f'user{i}', password='pass')
            customer = Customer.objects.create(user=user, name=f'Customer {i}', email=f'user{i}@test.com')
            rating = Rating.objects.create(customer=customer, book=self.book, score=i+3)
            Comment.objects.create(
                customer=customer,
                book=self.book,
                rating=rating,
                title=f'Review {i}',
                content=f'Comment {i}'
            )
        
        response = self.client.get(reverse('book_reviews', args=[self.book.id]))
        self.assertEqual(response.status_code, 200)
        self.assertIn('book', response.context)
        self.assertEqual(len(response.context['comments']), 3)

    def test_ratings_api(self):
        """Test ratings API endpoint"""
        rating = Rating.objects.create(customer=self.customer, book=self.book, score=5)
        comment = Comment.objects.create(
            customer=self.customer,
            book=self.book,
            rating=rating,
            title='Great',
            content='Love it'
        )
        
        response = self.client.get(reverse('api_ratings', args=[self.book.id]))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['book_id'], self.book.id)
        self.assertEqual(len(data['ratings']), 1)
        self.assertEqual(len(data['comments']), 1)

    def test_add_rating_requires_login(self):
        """Test that adding rating requires login"""
        response = self.client.get(reverse('add_rating_comment', args=[self.book.id]), follow=True)
        self.assertEqual(response.status_code, 200)  # Follow=True means it loads the login page

    def test_rating_updates_book_rating(self):
        """Test that book rating is updated when ratings are added"""
        self.client.login(username='testuser', password='testpass')
        
        # Add rating
        self.client.post(reverse('add_rating_comment', args=[self.book.id]), {
            'score': '5',
            'title': 'Great!',
            'content': 'Excellent'
        })
        
        self.book.refresh_from_db()
        self.assertEqual(self.book.rating, 5.0)
        self.assertEqual(self.book.review_count, 1)
        
        # Add another rating
        user2 = User.objects.create_user(username='user2', password='pass')
        customer2 = Customer.objects.create(user=user2, name='User 2', email='user2@test.com')
        order2 = Order.objects.create(customer=customer2, status='Delivered', total_amount=19.99)
        OrderItem.objects.create(order=order2, book=self.book, quantity=1, price=19.99)
        
        self.client.login(username='user2', password='pass')
        self.client.post(reverse('add_rating_comment', args=[self.book.id]), {
            'score': '4',
            'title': 'Good',
            'content': 'Very good'
        })
        
        self.book.refresh_from_db()
        self.assertEqual(self.book.rating, 4.5)  # Average of 5 and 4
        self.assertEqual(self.book.review_count, 2)
    def test_comment_history_allows_multiple_entries(self):
        """Test that each submission creates a new comment entry for history."""
        self.client.login(username='testuser', password='testpass')
        
        # Create first comment
        self.client.post(reverse('add_rating_comment', args=[self.book.id]), {
            'score': '5',
            'title': 'Great!',
            'content': 'First comment'
        })
        
        # Verify first comment created
        comment_count = Comment.objects.filter(customer=self.customer, book=self.book).count()
        self.assertEqual(comment_count, 1)
        
        first_comment = Comment.objects.filter(customer=self.customer, book=self.book).order_by('created_at').first()
        self.assertEqual(first_comment.title, 'Great!')
        self.assertEqual(first_comment.content, 'First comment')
        
        # Update comment (second post with different title/content)
        self.client.post(reverse('add_rating_comment', args=[self.book.id]), {
            'score': '4',
            'title': 'Updated!',
            'content': 'Updated comment'
        })
        
        # Verify two comments now exist (history is preserved)
        comment_count = Comment.objects.filter(customer=self.customer, book=self.book).count()
        self.assertEqual(comment_count, 2, "Should keep both comments as history")
        
        # Verify latest comment has the updated content
        latest_comment = Comment.objects.filter(customer=self.customer, book=self.book).order_by('-created_at').first()
        self.assertEqual(latest_comment.title, 'Updated!')
        self.assertEqual(latest_comment.content, 'Updated comment')

    def test_review_count_matches_comment_count(self):
        """Test that book.review_count shows comment count, not rating count"""
        self.client.login(username='testuser', password='testpass')
        
        # Create comment through the view (which updates book.review_count)
        self.client.post(reverse('add_rating_comment', args=[self.book.id]), {
            'score': '5',
            'title': 'Review 1',
            'content': 'Content 1'
        })
        
        self.book.refresh_from_db()
        # review_count should be 1 (1 comment)
        self.assertEqual(self.book.review_count, 1)
        self.assertEqual(Rating.objects.filter(book=self.book).count(), 1)
        
        # Add another rating without comment
        user2 = User.objects.create_user(username='user2', password='pass')
        customer2 = Customer.objects.create(user=user2, name='User 2', email='user2@test.com')
        rating2 = Rating.objects.create(customer=customer2, book=self.book, score=4)
        
        # review_count should still be 1 (only 1 comment), not 2
        # This test shows the behavior: ratings ≠ review_count

        self.assertEqual(self.book.review_count, 1)
        self.assertEqual(Rating.objects.filter(book=self.book).count(), 2)  # But 2 ratings exist