# Bookstore Django Project - Comprehensive Architecture Analysis

**Last Updated:** March 9, 2026  
**Project Type:** Django E-Commerce Application  
**Database:** SQLite (development)

---

## Executive Summary

This is a Django-based bookstore e-commerce platform with:
- 16 core models managing books, inventory, orders, customers, payments, and ratings
- 5 main feature domains (Books, Orders, Customers, Ratings, Recommendations)
- Mix of template-based views and JSON API endpoints
- Integrated payment and shipping services
- User authentication via Django's built-in auth

**Key Finding:** The system is moderately coupled with several features that could be extracted into microservices. Authentication is tightly coupled to Django's User model.

---

## 1. DATA MODELS & RELATIONSHIPS

### 1.1 Model Hierarchy

```
User (Django Auth)
├── Customer (1:1)
│   ├── Order (1:M)
│   │   ├── OrderItem (1:M)
│   │   │   └── Book (M:1)
│   │   ├── Payment (1:1)
│   │   └── Shipment (1:1)
│   ├── Rating (1:M) → Book
│   ├── Comment (1:M) → Book
│   └── Cart (1:1)
│       └── CartItem (1:M) → Book
├── Staff (1:1)
├── UserProfile (1:1)
└── Recommendation (1:M) → Book

Book
├── BookDetail (1:1)
├── BookImage (1:M)
├── Category (referenced as CharField - NOT FK)
├── Author (referenced as CharField - NOT FK)
├── Rating (1:M) ← Customer
├── Comment (1:M) ← Customer
├── Inventory (1:1)
└── OrderItem (1:M) ← Order

Author (standalone - NO relationships)
├── Imported but not used in foreign keys
└── Stored separately from Book.author (CharField)

Category (standalone - NO relationships)
├── Imported but not used in foreign keys
└── Stored separately from Book.category (CharField)
```

### 1.2 Detailed Model Specifications

#### **Book** (Central entity)
```
- title (CharField, max 255)
- author (CharField, max 255) ⚠️ String, not FK to Author
- price (DecimalField, 10,2)
- stock (PositiveIntegerField)
- category (CharField, 100) ⚠️ String, not FK to Category
- description (TextField)
- rating (DecimalField, 2,1) - Denormalized aggregate
- review_count (PositiveIntegerField) - Denormalized aggregate
- created_at / updated_at (auto timestamps)

Relationships:
- 1:1 BookDetail (extended info)
- 1:M BookImage (multiple images)
- 1:1 Inventory (stock tracking)
- 1:M OrderItem (purchased in orders)
- 1:M Rating (customer ratings)
- 1:M Comment (customer reviews)
- M:M Recommendation (via through model)
```

#### **BookDetail**
```
- book (OneToOneField → Book, CASCADE, related_name='detail')
- language (CharField, 50)
- number_of_pages (PositiveIntegerField)
- publisher (CharField, 255)
```

#### **BookImage**
```
- book (ForeignKey → Book, CASCADE, related_name='images')
- image (ImageField, upload_to='books/images/')
- is_cover (BooleanField)
```

#### **Author** ⚠️ ORPHANED
```
- name (CharField, 255)
- biography (TextField)
⚠️ Created in models but NOT linked to Book
⚠️ No foreign key relationship despite being a separate model
```

#### **Category** ⚠️ ORPHANED
```
- name (CharField, 150)
- description (TextField)
⚠️ Created in models but NOT linked to Book
⚠️ No foreign key relationship despite being a separate model
```

#### **Inventory**
```
- book (OneToOneField → Book, CASCADE, related_name='inventory')
- quantity (IntegerField)
⚠️ Duplicates Book.stock - potential data inconsistency
```

#### **Customer**
```
- user (OneToOneField → Django User, CASCADE, nullable)
- name (CharField, 255)
- email (EmailField)
- phone (CharField, 20)
- address (TextField)

Relationships:
- 1:1 Django User
- 1:M Order (via FK in Order)
- 1:M Rating (via FK in Rating)
- 1:M Comment (via FK in Comment)
- 1:1 Cart (via FK in Cart)
```

#### **Cart**
```
- user (ForeignKey → Django User, CASCADE, nullable)
- created_at (auto timestamp)

Relationships:
- 1:M CartItem
  - Each CartItem.book → Book
```

#### **Order**
```
- customer (ForeignKey → Customer, CASCADE)
- status (CharField, 50) - Values: 'Pending', 'Confirmed', 'Paid', 'Payment Failed', 'Shipped', 'Delivered', 'Refunded'
- total_amount (DecimalField, 10,2)
- created_at (auto timestamp)

Relationships:
- M:1 Customer (many orders per customer)
- 1:M OrderItem (line items)
- 1:1 Payment
- 1:1 Shipment
```

#### **OrderItem**
```
- order (ForeignKey → Order, CASCADE, related_name='items')
- book (ForeignKey → Book, CASCADE)
- quantity (PositiveIntegerField)
- price (DecimalField, 10,2) - Snapshot of book price at purchase time

Purpose: Line item in an order; captures price at time of purchase (denormalized)
```

#### **Payment**
```
- order (OneToOneField → Order, CASCADE)
- method_name (CharField, 50) - Values: 'Credit Card', 'Debit Card', 'Digital Wallet', 'Cash on Delivery'
- amount (DecimalField, 10,2)
- status (CharField, 30) - Values: 'Pending', 'Completed', 'Failed', 'Refunded'

Relationships:
- 1:1 Order
```

#### **Shipment**
```
- order (OneToOneField → Order, CASCADE)
- address (TextField)
- status (CharField, 50) - Values: 'Pending', 'Processing', 'Shipped', 'In Transit', 'Delivered', 'Failed'
- method_name (CharField, 50) - Values: 'Standard Shipping', 'Express Shipping', 'Overnight Shipping'
- fee (FloatField)

Relationships:
- 1:1 Order
```

#### **Rating**
```
- customer (ForeignKey → Customer, CASCADE, related_name='ratings_given')
- book (ForeignKey → Book, CASCADE, related_name='ratings')
- score (IntegerField) - Choices: 1-5 stars
- created_at / updated_at (auto timestamp)

Constraints:
- unique_together = ('customer', 'book') - One rating per customer per book
- ordering = ['-created_at']
```

#### **Comment**
```
- customer (ForeignKey → Customer, CASCADE, related_name='comments_made')
- book (ForeignKey → Book, CASCADE, related_name='comments')
- rating (ForeignKey → Rating, CASCADE, nullable, related_name='comments')
- title (CharField, 200)
- content (TextField)
- is_verified_purchase (BooleanField) - True if customer bought the book
- helpful_count (PositiveIntegerField) - Vote count
- created_at / updated_at (auto timestamp)

Constraints:
- unique_together = ('customer', 'book') - One comment per customer per book
- ordering = ['-helpful_count', '-created_at']
```

#### **Recommendation**
```
- user (ForeignKey → Django User, CASCADE)
- recommended_books (ManyToManyField → Book)
- generated_at (auto timestamp)

Note: Uses separate M:M relation, not related to Rating/Comment
```

#### **UserProfile**
```
- user (OneToOneField → Django User, CASCADE)
- full_name (CharField, 255)
- phone (CharField, 30)
- date_of_birth (DateField)
- avatar (ImageField, upload_to='avatars/')

⚠️ Partially duplicates Customer data (name, phone)
```

#### **Staff**
```
- user (OneToOneField → Django User, CASCADE, nullable)
- name (CharField, 255)
- role (CharField, 100)

Minimal usage - only 1 endpoint (staff_home)
```

### 1.3 Data Consistency Issues

| Issue | Impact | Severity |
|-------|--------|----------|
| Book.stock vs Inventory.quantity (duplicate) | Potential inconsistency | 🔴 HIGH |
| Author model orphaned (CharField instead of FK) | Can't query books by author relationship | 🟡 MEDIUM |
| Category model orphaned (CharField instead of FK) | Can't query category relationships | 🟡 MEDIUM |
| Book.rating/review_count denormalized | Must update on every rating change | 🟡 MEDIUM |
| UserProfile + Customer both store personal info | Data duplication | 🟡 MEDIUM |
| Cart tied to Django User, not Customer | Inconsistent access patterns | 🟡 MEDIUM |

---

## 2. VIEW/CONTROLLER LOGIC & DATA FLOW

### 2.1 Controllers Organization

```
controllers/
├── api_views.py                    # JSON API endpoints
├── bookController/
│   ├── views.py                    # Book browsing/search
│   ├── cart_views.py               # Shopping cart management
│   ├── rating_comment_views.py     # Ratings and reviews
│   └── recommendation_views.py     # Book recommendations
├── orderController/
│   ├── views.py                    # Order listing/tracking
│   ├── checkout_views.py           # Checkout/Order creation
│   └── payment_shipping_views.py   # Payment & shipping processing
├── customerController/
│   └── views.py                    # Auth, customer dashboard
└── staffController/
    └── views.py                    # Staff portal (minimal)
```

### 2.2 Book Feature Controllers

#### **bookController/views.py** - Book Browsing
```
book_list(request):
  ├─ Reads: Book (all)
  ├─ Filters: search (title/author), categories, price range, rating, stock
  ├─ Sorting: name, price_low, price_high, rating
  ├─ Pagination: 12 books per page
  ├─ Writes: None
  └─ Output: book/list.html template

book_detail(request, book_id):
  ├─ Reads: Book by ID
  ├─ Output: book/detail.html template
  └─ No writes, static content display
```

**Data Flow:**
- User → book_list → Database query → Template rendering
- Single pass, read-only

#### **bookController/cart_views.py** - Shopping Cart
```
add_to_cart(request, book_id):
  ├─ Requires: Login
  ├─ Reads: Book, Cart (get_or_create), CartItem (get_or_create)
  ├─ Writes: CartItem.quantity += 1
  ├─ Logic: Uses get_or_create for both Cart and CartItem
  └─ Redirect: /cart/

remove_from_cart(request, book_id):
  ├─ Requires: Login
  ├─ Reads: Cart
  ├─ Writes: Delete CartItem
  └─ Redirect: /cart/

cart_view(request):
  ├─ No login required
  ├─ Reads: Cart.items with Book.price
  ├─ Calculates: total = sum(item.book.price * item.quantity)
  ├─ Calculations: Tax = 8%, Total = cart_total + tax
  └─ Output: cart/cart_improved.html
```

**Data Flow:**
- User → add_to_cart → Update CartItem → Recalculate on view

#### **bookController/rating_comment_views.py** - Ratings & Reviews
```
add_rating_comment(request, book_id):
  ├─ Requires: Login
  ├─ Reads: Book, Customer, OrderItem (to verify purchase), Rating, Comment
  ├─ Writes:
  │  ├─ Rating.update_or_create(customer, book, score)
  │  └─ Comment.update_or_create(customer, book, content)
  ├─ Updates Book: 
  │  ├─ book.rating = avg(Rating.score) [rounded to 1 decimal]
  │  └─ book.review_count = count(Comment)
  ├─ Logic: Checks OrderItem for verified_purchase flag
  └─ Redirect: book_detail

mark_helpful(request, comment_id):
  ├─ Writes: comment.helpful_count += 1
  ├─ Returns: AJAX response or redirect
  └─ No auth check (potential security issue)

book_reviews(request, book_id):
  ├─ Reads: Rating (all for book), Comment (all for book)
  ├─ Calculates: Rating breakdown (1-5 star counts), average rating
  ├─ Sorting: Comments by [-helpful_count, -created_at]
  └─ Output: book/reviews.html

get_ratings_api(request, book_id):
  ├─ JSON API endpoint
  ├─ Returns: ratings and comments as JSON
  ├─ No pagination implemented
  └─ Exposes customer names in API
```

**Data Flow:**
- User purchases → OrderItem created → User can rate → Ratings aggregate to Book.rating
- Async: mark_helpful updates without page reload

#### **bookController/recommendation_views.py** - Recommendations
```
data_model_recommendation(request):
  ├─ Requires: Login
  ├─ Reads: Book.objects.order_by('?')[:5]
  ├─ Logic: Random books (NOT personalized)
  ├─ Query: SELECT * FROM book ORDER BY RANDOM() LIMIT 5
  └─ Output: recommendation/list.html

⚠️ Current implementation: Just random books
⚠️ Not using Recommendation model at all
⚠️ No collaborative filtering or purchase history analysis
```

### 2.3 Order Feature Controllers

#### **orderController/checkout_views.py** - Order Creation
```
checkout(request):
  ├─ Requires: Login
  ├─ Reads: Cart, CartItems with Books, Customer
  ├─ Writes:
  │  ├─ Order (new)
  │  ├─ OrderItem × N (for each cart item)
  │  ├─ Shipment (via ShippingService)
  │  └─ Book.stock -= quantity (inventory reduction)
  ├─ Business Logic:
  │  ├─ Validates: full_name, email, address required
  │  ├─ Calculates: subtotal, tax (8%), shipping_fee
  │  ├─ total = subtotal + tax + shipping_fee
  │  └─ ShippingService.create_shipment()
  ├─ Session: Stores order_id, shipment_id
  └─ Redirect: payment_initiate

payment_confirm(request, order_id):
  ├─ Requires: Login + customer ownership check
  ├─ Reads: Order, Shipment
  ├─ Method: POST with payment method (credit_card, debit_card, wallet, cod)
  ├─ Writes:
  │  ├─ Payment.create (via PaymentService)
  │  ├─ Payment.process_payment (always succeeds in demo)
  │  ├─ Order.status = 'Confirmed'
  │  └─ Cart.items.delete()
  ├─ Returns: order/success.html
  └─ Note: No actual payment gateway integration

cart_view(request):
  ├─ No auth required
  ├─ Calculates: cart_total, tax (8%), total
  └─ Output: cart/cart_improved.html
```

**Data Flow:**
```
Cart → Checkout → Order + OrderItem + Shipment → Payment → Success
                           ↓
                    Reduce Book.stock
```

#### **orderController/payment_shipping_views.py** - Payment Processing
```
payment_initiate(request, order_id):
  ├─ GET: Shows payment method selector
  ├─ POST: Creates Payment record
  ├─ Logic:
  │  ├─ COD (Cash on Delivery): status='Pending'
  │  └─ Other: status='Completed' (simulated approval)
  └─ Redirect: payment_success

payment_success(request, order_id):
  ├─ Reads: Order, Payment
  └─ Output: order/payment_success.html

payment_api(request, order_id):
  ├─ JSON endpoint
  ├─ Returns: payment_id, success status
  └─ Always succeeds (no error handling for real)

shipping_select(request, order_id):
  ├─ GET: Shows shipping options with fees
  ├─ POST: Creates Shipment record
  ├─ ShippingService.create_shipment(order, method, address, fee)
  └─ Shipment.status = 'Pending'
```

**Shipping Options:**
```
- Standard: $5.00 base + $1.50/weight = 5 days
- Express: $15.00 base + $1.50/weight = 2 days
- Overnight: $30.00 base + $1.50/weight = 1 day
```

### 2.4 Customer Feature Controllers

#### **customerController/views.py** - Auth & Dashboard
```
register(request):
  ├─ POST: Creates Django User via UserCreationForm
  ├─ Writes:
  │  ├─ User (via form.save())
  │  └─ Customer.create(user=user, name, email)
  └─ Redirect: / (auto-login)

login_view(request):
  ├─ POST: Django auth
  └─ Redirect: /

logout_view(request):
  ├─ Clears session
  └─ Redirect: /

customer_home(request):
  ├─ Requires: Login
  ├─ Reads:
  │  ├─ Customer profile
  │  ├─ Order (all for customer, with filters)
  │  ├─ OrderItem (aggregation for total_books)
  │  └─ Order summaries (count, amounts)
  ├─ Filters:
  │  ├─ By status
  │  ├─ By date range (start_date, end_date)
  │  └─ By page_size (1-50)
  ├─ Pagination: Configurable page size
  ├─ Calculates:
  │  ├─ total_orders = count
  │  ├─ total_books = sum(OrderItem.quantity)
  │  └─ total_spent = sum(Order.total_amount)
  └─ Output: customer/dashboard template with stats
```

**Dashboard Stats:**
- Total Orders (count)
- Total Books Purchased (sum of quantities)
- Total Amount Spent
- Order list with filtering/sorting

### 2.5 Staff Controllers

#### **staffController/views.py**
```
staff_home(request):
  ├─ Requires: No auth checks (⚠️ SECURITY ISSUE)
  └─ Output: staff/home.html (likely empty)

⚠️ ISSUE: No permission checks, staff pages accessible to anyone
⚠️ ISSUE: Minimal implementation, no staff functionality
```

### 2.6 API Views

#### **api_views.py** - JSON Endpoints
```
book_list_api(request):
  ├─ Returns: JSON list of all books with: id, title, author, price, stock, category
  └─ Scope: No pagination implemented (returns all books)

book_detail_api(request, book_id):
  ├─ Handles 404 with Http404
  ├─ Returns: id, title, author, price, stock, category, description, rating, review_count
  └─ Price converted to float

author_list_api(request):
  ├─ Returns: JSON list of all authors (id, name)
  └─ Scope: Author model not actually linked to books

author_detail_api(request, author_id):
  ├─ Returns: Full author data (model_to_dict)
  └─ Limited value without book relationships

⚠️ ISSUE: No authentication on API endpoints
⚠️ ISSUE: No pagination for list endpoints
⚠️ ISSUE: Author/Category endpoints don't reflect actual data relationships
```

---

## 3. SERVICES & BUSINESS LOGIC

### 3.1 Service Architecture

```
services/
├── payment_shipping_service.py    # Payment & Shipping logic
└── recommendation.py              # Book recommendations
```

### 3.2 PaymentService

**Location:** `store/services/payment_shipping_service.py`

```python
class PaymentService:
    PAYMENT_METHODS = {
        'credit_card': 'Credit Card',
        'debit_card': 'Debit Card',
        'wallet': 'Digital Wallet',
        'cod': 'Cash on Delivery'
    }
    
    @staticmethod
    def create_payment(order, method, amount):
        # Creates Payment record with status='Pending'
        # No external gateway integration
        
    @staticmethod
    def process_payment(payment, is_successful=True):
        # Updates payment.status = 'Completed' or 'Failed'
        # Also updates Order.status = 'Paid' or 'Payment Failed'
        # ⚠️ DEMO ONLY: No actual payment processing
        
    @staticmethod
    def refund(payment):
        # Updates payment.status = 'Refunded'
        # Updates order.status = 'Refunded'
        # Raises ValueError if not 'Completed'
```

**Current Limitations:**
- No actual payment gateway (Stripe, PayPal, etc.)
- No encryption or PCI compliance
- No webhook handling
- No idempotency keys
- No payment retry logic

### 3.3 ShippingService

**Location:** `store/services/payment_shipping_service.py`

```python
class ShippingService:
    SHIPPING_METHODS = {
        'standard': {'name': 'Standard Shipping', 'fee': Decimal('5.00'), 'days': 5},
        'express': {'name': 'Express Shipping', 'fee': Decimal('15.00'), 'days': 2},
        'overnight': {'name': 'Overnight Shipping', 'fee': Decimal('30.00'), 'days': 1},
    }
    
    @staticmethod
    def calculate_shipping_fee(method, weight=1.0):
        # base_fee + (weight * 1.5)
        # Example: standard with 1.0kg = $5 + $1.50 = $6.50
        
    @staticmethod
    def create_shipment(order, method, address, fee):
        # Creates Shipment record with status='Pending'
        
    @staticmethod
    def update_shipment_status(shipment, status):
        # Valid statuses: 'Pending', 'Processing', 'Shipped', 'In Transit', 'Delivered', 'Failed'
        # Syncs Order.status with Shipment.status
        
    @staticmethod
    def get_shipping_options(weight=1.0):
        # Returns dict with all options and calculated fees
```

**Workflow:**
1. Customer selects shipping method at checkout
2. Service calculates fee based on method + weight
3. Shipment record created with fee
4. Fee added to order total

**Current Limitations:**
- Weight parameter unused (always defaults to 1.0)
- No real carrier integration (FedEx, UPS, DHL)
- No tracking API
- Addresses stored as plain text, no validation
- Fee calculation is simplistic

### 3.4 Recommendation Service

**Location:** `store/services/recommendation.py`

```python
def recommend_books(book, limit=4):
    return Book.objects.exclude(id=book.id)[:limit]
```

**Current Implementation:**
- Just returns random other books
- Not imported or used anywhere
- No actual recommendation logic
- No user history analysis

**Unused Model:**
- `Recommendation` model exists but not used by this service
- M:M relationship with books defined but never populated

---

## 4. API ENDPOINTS & URL ROUTING

### 4.1 URL Configuration

**Main Router:** `bookstore/urls.py`
```python
urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("store.urls.book_urls")),
    path("order/", include("store.urls.order_urls")),
    path("customer/", include("store.urls.customer_urls")),
    path("staff/", include("store.urls.staff_urls")),
]
```

### 4.2 Book URLs

**File:** `store/urls/book_urls.py`

| Method | Endpoint | View | Purpose | Auth |
|--------|----------|------|---------|------|
| GET | `/` | `book_list` | Browse all books with filters | No |
| GET | `/api/books/` | `book_list_api` | JSON list of books | No |
| GET | `/<book_id>/` | `book_detail` | Book detail page | No |
| GET | `/api/books/<book_id>/` | `book_detail_api` | JSON book detail | No |
| GET | `/api/books/<book_id>/ratings/` | `get_ratings_api` | JSON ratings + comments | No |
| GET/POST | `/<book_id>/rate/` | `add_rating_comment` | Add/edit rating & review | **Yes** |
| GET | `/<book_id>/reviews/` | `book_reviews` | All reviews for book | No |
| POST | `/comment/<comment_id>/helpful/` | `mark_helpful` | Vote helpful on comment | No |
| GET | `/cart/` | `cart_view` | View shopping cart | No |
| POST | `/add/<book_id>/` | `add_to_cart` | Add item to cart | **Yes** |
| POST | `/remove/<book_id>/` | `remove_from_cart` | Remove from cart | **Yes** |
| GET | `/recommendations/` | `data_model_recommendation` | Get recommendations | **Yes** |
| GET | `/api/authors/` | `author_list_api` | JSON author list | No |
| GET | `/api/authors/<author_id>/` | `author_detail_api` | JSON author detail | No |

### 4.3 Order URLs

**File:** `store/urls/order_urls.py`

| Method | Endpoint | View | Purpose | Auth |
|--------|----------|------|---------|------|
| POST | `/add/<book_id>/` | `add_to_cart` | Add to cart | **Yes** |
| POST | `/remove/<book_id>/` | `remove_from_cart` | Remove from cart | **Yes** |
| GET | `/cart/` | `cart_view` | View cart | No |
| GET/POST | `/checkout/` | `checkout` | Create order | **Yes** |
| GET/POST | `/<order_id>/payment/` | `payment_confirm` | Process payment | **Yes** |
| GET | `/<order_id>/success/` | `order_success` | Order success page | **Yes** |
| GET | `/track/<shipment_id>/` | `track_shipment` | Track shipment | ? |

### 4.4 Customer URLs

**File:** `store/urls/customer_urls.py`

| Endpoint | View | Purpose |
|----------|------|---------|
| POST | `/customer/register/` | User registration |
| POST | `/customer/login/` | User login |
| GET | `/customer/logout/` | User logout |
| GET | `/customer/profile/` | Customer dashboard | **Yes** |

### 4.5 Staff URLs

**File:** `store/urls/staff_urls.py`

| Endpoint | View | Purpose |
|----------|------|---------|
| GET | `/staff/` | Staff home page |

### 4.6 Endpoint Security Issues

| Issue | Severity | Description |
|-------|----------|-------------|
| No auth on `/api/books/` | 🟡 MEDIUM | Lists all books (probably OK) |
| No auth on `book_reviews` | 🟡 MEDIUM | Could expose customer names |
| No auth on `get_ratings_api` | 🟡 MEDIUM | Exposes customer info in JSON |
| No auth on `mark_helpful` | 🔴 HIGH | Anyone can boost comment votes |
| No rate limiting | 🔴 HIGH | API endpoints could be abused |
| No pagination on API lists | 🟡 MEDIUM | Could return huge datasets |
| Staff page has no auth check | 🔴 HIGH | Accessible to anyone |

---

## 5. DATABASE SCHEMA RELATIONSHIPS

### 5.1 Entity-Relationship Diagram

```
                     ┌─────────────┐
                     │  Django User│
                     │  (Built-in) │
                     └────┬────────┘
                          │ OneToOne
                    ┌─────┴────────────┬─────────────┬────────────┐
                    │                  │             │            │
              ┌─────▼────┐      ┌──────▼──┐    ┌─────▼─────┐  ┌──▼──────┐
              │ Customer │      │  Staff  │    │ UserProfile│ │ Cart    │
              └─────┬────┘      └─────────┘    └────────────┘ └──┬──────┘
                    │                                            │ OneToMany
                    │ OneToMany                             ┌────▼────┐
                    │                                        │CartItem │
                    │                                        └────┬────┘
              ┌─────▼────┐                                        │ FK
              │  Order   │                                        │
              └─────┬────┘                                   ┌────▼────┐
                    │ OneToMany                              │  Book   │
                    │                                        └────┬────┘
              ┌─────▼────────┐                                   │
              │  OrderItem   │◄─────────────────────────────────┘
              └──────────────┘                             OneToMany
                    │ FK
                    │
              ┌─────▼────┐
              │  Book    │
              └─────┬────┘
                    │
         ┌──────────┼──────────┬───────────────┬┐
         │          │          │               │└─────────┐
    ┌────▼─┐  ┌─────▼────┐ ┌──▼──────┐  ┌────▼───┐   ┌───▼───────┐
    │ Rating│◄──┤ Book    │ │BookDetail├─→│BookImage│   │ Inventory │
    └────┬──┘  │          │ └─────────┘  └────────┘   └───────────┘
         │     └──────────┘
         │ FK Customer    
    ┌────▼────┐
    │ Comment │
    └────┬────┘
         │ FK Comment.rating ──Ratings
         │
    ┌────▼──────┐
    │Order Payment│
    └────────────┘
    
    ┌──────────────┐
    │ Order.Shipment│
    └──────────────┘
    
    ┌─────────────┐
    │Recommendation│ ──(M:M)──→ Book
    └─────────────┘
```

### 5.2 Denormalized Fields

| Model | Field | Purpose | Update Frequency | Consistency Risk |
|-------|-------|---------|------------------|------------------|
| Book | rating | Average rating | On every new rating | Not recalculated if rating deleted |
| Book | review_count | Review count | On comment create/update | Not recalculated on deletion |
| OrderItem | price | Historical price | One-time at order | ✓ (immutable) |
| Book | stock | Current inventory | On checkout | Could diverge from Inventory.quantity |

### 5.3 Foreign Key Cascade Rules

All relationships use `CASCADE` delete. Impact:
- Delete Book → Deletes BookDetail, BookImage, OrderItem, Rating, Comment, Inventory
- Delete Customer → Deletes Order, Cart (and cascades)
- Delete Order → Deletes OrderItem, Payment, Shipment
- Delete Rating → Deletes Comment references

**Risk:** No soft deletes - data loss on deletion

---

## 6. EXTERNAL DEPENDENCIES & INTEGRATIONS

### 6.1 External Libraries

```python
# Django built-ins
from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.http import JsonResponse, Http404, HttpResponseRedirect
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Sum, Count, Q, Avg
from django.forms.models import model_to_dict
from django.conf import settings

# No third-party payment/shipping integrations
# ⚠️ Payment/Shipping are mocked/simulated
```

### 6.2 Payment Gateway Integration

**Current Status:** ❌ NOT IMPLEMENTED
- No Stripe, PayPal, or other gateway
- `PaymentService.process_payment()` always succeeds
- No tokenization or card storage
- Not PCI compliant

**For Production Needed:**
- Stripe SDK / Gumroad / 2Checkout
- Webhook handling for payment confirmation
- Card tokenization for recurring payments
- Fraud detection integration

### 6.3 Shipping Integration

**Current Status:** ❌ NOT IMPLEMENTED
- No FedEx, UPS, or USPS API integration
- Addresses stored as plain text
- No carrier rate shopping
- No shipping label generation
- No tracking URL creation

**For Production Needed:**
- EasyPost / ShipStation SDK
- Real carrier API for rates
- Address validation (USPS/UPU)
- Tracking synchronization

### 6.4 Authentication

**Current Status:** ✓ BASIC
- Uses Django's built-in User model
- No OAuth / Social login
- No email verification
- No password reset flow

### 6.5 Media Handling

```
static/store/
    └── (CSS, JavaScript, images)

Media files (ImageField):
- BookImage → upload_to='books/images/'
- UserProfile.avatar → upload_to='avatars/'

⚠️ In production: Need S3/Cloud storage
```

### 6.6 Email Integration

**Current Status:** ❌ NOT CONFIGURED
- No email backend configured
- No order confirmation emails
- No shipment notifications
- No password reset emails

---

## 7. FEATURE ANALYSIS: COUPLING & INDEPENDENCE

### 7.1 Feature Domains

```
Domain Architecture:
├── 🟦 Book Catalog (Independent-ish)
├── 🟦 Shopping Cart (Coupled to Book)
├── 🟦 Order Management (Tightly Coupled)
├── 🟦 Payment Processing (Coupled to Order)
├── 🟦 Shipping Management (Coupled to Order)
├── 🟦 Authentication (Coupled to Customer)
├── 🟦 Ratings & Reviews (Independent-ish)
└── 🟦 Recommendations (Decoupled)
```

### 7.2 Dependency Matrix

```
               Cart Order Payment Shipping Review Auth Recommend
Cart            -   ✓     -       -        -      ✓    -
Order           ✓   -     ✓       ✓        -      ✓    -
Payment         -   ✓     -       -        -      -    -
Shipping        -   ✓     -       -        -      -    -
Review          ✓   ✓     -       -        -      ✓    -
Auth            -   ✓     -       -        -      -    -
Recommend       ✓   -     -       -        -      -    -

Legend: ✓ = Depends on, - = Independent
```

### 7.3 Tight Coupling Points

| Coupling | Severity | Details |
|----------|----------|---------|
| Order ↔ Payment | 🔴 HIGH | Payment has OneToOne to Order; Order.status updated by Payment; Can't process payment without Order |
| Order ↔ Shipment | 🔴 HIGH | Shipment has OneToOne to Order; Status sync bidirectional |
| Cart ↔ Order | 🔴 HIGH | Checkout reads Cart, deletes Cart; Ephemeral Cart data |
| Book ↔ Rating | 🟡 MEDIUM | Book.rating denormalized; Rating needs to update Book on every change |
| Order ↔ Auth | 🟡 MEDIUM | Order.customer → Customer → User; Can't order without Django User |
| Customer ↔ Auth | 🟡 MEDIUM | Customer tied to Django User; OneToOne relationship required |

### 7.4 Feature Independence Assessment

#### ✅ **INDEPENDENT FEATURES**

**1. Recommendations Service**
```
- ✓ No dependencies on Cart, Order, or Payment
- ✓ Read-only from Book model
- ✗ Currently not implemented (returns random)
- ✗ Uses separate Django User, not Customer
- → Could be extracted as recommendation microservice
```

**2. Book Catalog (with caveats)**
```
- ✓ Independent browsing (no checkout needed)
- ✓ Can display without authentication
- ✗ Ratings/Review tightly coupled (updates Book.rating)
- ✗ Stock tied to checkout process
- → Could be separate catalog service with async rating updates
```

**3. Review/Rating System**
```
- ✓ Independent feature domain
- ✓ Separate from order workflow
- ✗ Requires order history verification (OrderItem check)
- ✗ Updates Book.rating (write dependency)
- → Could be separate review service with async updates
```

#### 🔴 **TIGHTLY COUPLED FEATURES**

**1. Order → Payment → Shipping (Workflow)**
```
- ✗ Sequential dependency: Order must exist before Payment
- ✗ Order → Shipment dependency: OneToOne constraint
- ✗ Order status synced with Payment and Shipment
- ✗ Cart deleted after order creation
- → CANNOT be extracted without major refactor
```

**2. Authentication**
```
- ✗ Django User hardcoded throughout system
- ✗ Customer OneToOne with User
- ✗ All protected views check Django Auth
- ✗ Staff model also tied to User
- → CANNOT be extracted; use existing auth service
```

**3. Cart (Ephemeral Data)**
```
- ✗ Tied to Django User (not Customer)
- ✗ Deleted on checkout
- ✗ Computed totals (no persistence)
- → Could be in-memory cache or Redis, but requires refactor
```

---

## 8. MICROSERVICES EXTRACTION OPPORTUNITIES

### 8.1 Extraction Feasibility Matrix

| Service | Feasibility | Effort | Value | Risk |
|---------|-------------|--------|-------|------|
| **Payment Gateway** | ⭐⭐⭐⭐⭐ | 1 day | 🟡 MEDIUM | 🔴 HIGH |
| **Shipping Service** | ⭐⭐⭐⭐⭐ | 2 days | 🟡 MEDIUM | 🟡 MEDIUM |
| **Recommendation Engine** | ⭐⭐⭐⭐ | 2-3 days | 🟢 HIGH | 🟢 LOW |
| **Review/Rating Service** | ⭐⭐⭐ | 3-5 days | 🟢 HIGH | 🟡 MEDIUM |
| **Inventory Service** | ⭐⭐⭐ | 2-3 days | 🟢 HIGH | 🔴 HIGH |
| **Search/Catalog** | ⭐⭐ | 5-7 days | 🟡 MEDIUM | 🟡 MEDIUM |
| **Notification Service** | ⭐⭐⭐⭐ | 2 days | 🟢 HIGH | 🟢 LOW |
| **Auth Service** | ⭐ | 10+ days | 🟢 HIGH | 🔴 CRITICAL |

### 8.2 Recommended Extraction Plan

#### **Phase 1: Easy Wins (Low Risk)**

**1. Payment Gateway Service** ⭐⭐⭐⭐⭐
```
Extract: PaymentService → Microservice
├─ Current: Mock implementation in Django
├─ Extract: Real payment gateway (Stripe/PayPal)
├─ Interface: HTTP API
├─ Independence: Order service calls Payment service
├─ Risk: Transaction consistency - use event sourcing
├─ Timeline: 1-2 days
└─ Benefit: Scalable, reusable for other platforms

API Design:
POST /api/payments
  └─ {order_id, amount, method, card_token}
  └─ Returns: {payment_id, status, transaction_id}

Webhook: On payment_completed event → Update Order
```

**2. Shipping Service** ⭐⭐⭐⭐⭐
```
Extract: ShippingService → Microservice
├─ Current: Hardcoded rates in code
├─ Extract: Real carrier APIs (EasyPost/ShipStation)
├─ Interface: HTTP API
├─ Features:
│   ├─ Rate shopping from multiple carriers
│   ├─ Address validation
│   ├─ Label generation
│   ├─ Tracking synchronization
├─ Risk: Addresses need validation before storage
├─ Timeline: 2-3 days
└─ Benefit: Multi-carrier support, real tracking

API Design:
POST /api/shipments
  └─ {order_id, address, method, weight}
  └─ Returns: {shipment_id, tracking_number, label_url}

Webhook: On status_changed event → Update Order
```

**3. Notification Service** ⭐⭐⭐⭐
```
Extract: Email/SMS notifications → Microservice
├─ Current: Not implemented
├─ Extract: Celery + Email/SMS queues
├─ Timeline: 1-2 days
└─ Notifications:
    ├─ Order confirmation
    ├─ Payment receipt
    ├─ Shipment notification
    ├─ Delivery confirmation
    └─ Review request

API Design:
Listen to events:
- order.created
- payment.completed
- shipment.shipped
- delivery.confirmed

Publish: email/sms to queue
```

#### **Phase 2: Medium Effort (Medium Risk)**

**4. Recommendation Engine** ⭐⭐⭐⭐
```
Extract: Recommendation → ML Microservice
├─ Current: Random books (unusable)
├─ Extract: Separate service with:
│   ├─ Collaborative filtering
│   ├─ Content-based filtering
│   ├─ User purchase history
│   ├─ Rating/review signals
├─ Timeline: 3-5 days
└─ Interface: gRPC or HTTP

Features:
- Real-time recommendations
- Batch retraining
- A/B testing capabilities
- User segmentation

Decoupling: Service calls recommendation API
No direct DB access needed
```

**5. Review & Rating Service** ⭐⭐⭐
```
Extract: Rating/Comment → Separate Service
├─ Current: Tightly coupled to Book.rating update
├─ Extract:
│   ├─ Review storage (separate DB)
│   ├─ Async rating aggregation
│   ├─ Review moderation workflow
│   └─ Helpfulness ranking
├─ Timeline: 3-5 days
├─ Risk: Book.rating needs async update
└─ Interface: HTTP API + event stream

Database: Separate DB for reviews (shardable)

API Design:
POST /api/reviews/books/{book_id}
  └─ {customer_id, rating, comment}

GET /api/reviews/books/{book_id}
  └─ Returns: paginated reviews, average rating
  
Event: rating.updated → Update Book.rating async
```

**6. Inventory Service** ⭐⭐⭐
```
Extract: Stock Management → Separate Service
├─ Current: Book.stock (single source of truth)
├─ Extract:
│   ├─ Inventory tracking
│   ├─ Stock reservations (cart → order)
│   ├─ Back-order management
│   └─ Warehouse management
├─ Timeline: 2-3 days
├─ Risk: Double-booking without proper locking
└─ Interface: HTTP API + event stream

Key Concept: Inventory Reservations
- Add to cart → Reserve stock (temporary hold)
- Checkout → Confirm reservation
- Auto-release on cart expiry

API Design:
POST /api/inventory/reserve
  └─ {book_id, quantity, user_id, ttl=15min}
  └─ Returns: reservation_id or "out of stock"

POST /api/inventory/confirm
  └─ {reservation_id}
  └─ Creates OrderItem, reduces inventory

POST /api/inventory/release
  └─ {reservation_id}
  └─ Releases hold, restores available stock
```

#### **Phase 3: Hard Refactor (High Risk)**

**7. Search & Catalog Service** ⭐⭐
```
Extract: Book Catalog → Separate Service
├─ Current: Monolithic Book model + views
├─ Extract: Separate service with Elasticsearch
├─ Timeline: 5-7 days
├─ Risk: Complex refactoring, data sync issues
└─ Benefits:
    ├─ Search performance (Elasticsearch)
    ├─ Faceted search
    ├─ Real-time indexing
    ├─ Advanced filtering

Architecture:
- Catalog Service DB: Books, Authors, Categories
- Search Index: Elasticsearch
- Data sync: Via events or batch
- Read path: Search service → Elasticsearch
```

**8. Authentication & Users → DO NOT EXTRACT** ⭐
```
Why:
├─ Rails/Django auth is proven, secure
├─ Extracting auth is risky (SSO complexity)
├─ All services depend on it
├─ OAuth2 for external APIs sufficient

Instead: Improve within Django
├─ Add email verification
├─ Add 2FA support
├─ Add OAuth providers
├─ Add API keys for apps
└─ Consider OAuth2 server (django-oauth-toolkit)
```

---

## 9. SUMMARY & RECOMMENDATIONS

### 9.1 Current Architecture Score

| Dimension | Score | Notes |
|-----------|-------|-------|
| **Modularity** | 5/10 | Controllers separated; models tightly coupled |
| **Scalability** | 4/10 | SQLite; no caching; no async tasks |
| **Maintainability** | 6/10 | Clear structure; some duplication |
| **Testability** | 4/10 | Few tests; tight Django coupling |
| **Security** | 3/10 | No auth on API; demo payment processing; CSRF not checked |
| **Performance** | 3/10 | N+1 queries likely; no pagination on API |
| **Reliability** | 4/10 | No error handling; cascade deletes risky |

### 9.2 Top Priority Issues

| Priority | Issue | Fix Effort | Impact |
|----------|-------|-----------|--------|
| 🔴 CRITICAL | Security: API endpoints unauthenticated | 4 hours | Prevents data leaks |
| 🔴 CRITICAL | Data consistency: Book.stock vs Inventory.quantity | 1 day | Risk of overselling |
| 🔴 CRITICAL | Payment processing not real | 2-3 days | Revenue at risk |
| 🟠 HIGH | Staff pages have no auth | 2 hours | Prevents unauthorized access |
| 🟠 HIGH | Author/Category models orphaned | 2-3 days | Can't query relationships |
| 🟠 HIGH | No email notifications | 1-2 days | Poor UX, lost orders |
| 🟡 MEDIUM | Denormalized ratings inconsistent | 4-6 hours | Corrupt data possible |
| 🟡 MEDIUM | Recommendations not implemented | 2-3 days | Feature unusable |

### 9.3 Recommended Next Steps

**Short Term (1-2 weeks):**
1. ✅ Integrate real payment gateway (Stripe)
2. ✅ Add authentication to API endpoints
3. ✅ Add email notifications
4. ✅ Fix Author/Category relationships
5. ✅ Implement inventory reservations

**Medium Term (1-2 months):**
1. ✅ Extract Payment Service → Microservice
2. ✅ Extract Shipping Service → Microservice
3. ✅ Implement real recommendations engine
4. ✅ Add caching layer (Redis)
5. ✅ Implement order audit trail

**Long Term (3-6 months):**
1. ✅ Extract Review Service → Microservice
2. ✅ Extract Inventory Service → Microservice
3. ✅ Implement search service (Elasticsearch)
4. ✅ Add analytics platform
5. ✅ Migrate to async workers (Celery)

### 9.4 Architecture Roadmap

```
Current State (Monolith):
┌──────────────────────────────────────┐
│  Django Monolith                     │
│  ├─ Book Catalog                     │
│  ├─ Cart Management                  │
│  ├─ Order Management                 │
│  ├─ Payment (Mocked)                 │
│  ├─ Shipping (Mocked)                │
│  ├─ Ratings & Reviews                │
│  ├─ Recommendations (Broken)         │
│  └─ Auth & Users                     │
└──────────────────────────────────────┘

Phase 1: Add Async & External Services
┌──────────────────────────────────────┐
│  Django Monolith                     │
│  ├─ Book Catalog                     │
│  ├─ Cart Management                  │
│  ├─ Order Management                 │
│  ├─ Ratings & Reviews                │
│  ├─ Auth & Users                     │
│  └─ Queues (Celery)                  │
├─────────────────────────────────────┤
│  Standalone Services                 │
│  ├─ Payment Service (Stripe)         │
│  ├─ Shipping Service (EasyPost)      │
│  ├─ Notification Service (Email/SMS) │
│  └─ Recommendation Engine (ML)       │
└──────────────────────────────────────┘

Phase 2: Domain Extraction
┌──────────────────┬──────────────────┬──────────────────┐
│  Auth Service    │  Catalog Service │ Recommendation   │
├──────────────────┼──────────────────┼──────────────────┤
│  Book DB         │  Book DB         │  ML Model        │
│  User DB         │  Cache           │  Redis           │
│  OAuth2 Server   │  Elasticsearch   │  Python Service  │
└──────────────────┴──────────────────┴──────────────────┘

┌──────────────────┬──────────────────┬──────────────────┐
│ Order Service    │  Review Service  │ Inventory Svc    │
├──────────────────┼──────────────────┼──────────────────┤
│  Order DB        │  Review DB       │  Inventory DB    │
│  Payment API     │  Moderation      │  Reservations    │
│  Shipping API    │  Aggregation     │  Warehouse Mgmt  │
└──────────────────┴──────────────────┴──────────────────┘

API Gateway / Load Balancer
├─ Orders Service API
├─ Catalog Service API
├─ Review Service API
├─ Recommendation API
├─ Auth Service API
└─ Inventory Service API
```

---

## Appendix: File Organization

### Project Structure Tree
```
bookstore/
├── bookstore/
│   ├── __init__.py
│   ├── settings.py          ← Main configuration
│   ├── urls.py              ← Main URL router
│   ├── asgi.py
│   └── wsgi.py
├── store/
│   ├── admin.py             ← Django admin config (25 models registered)
│   ├── apps.py
│   ├── models/
│   │   ├── __init__.py      ← All models imported here
│   │   ├── user_profile.py  ← UserProfile (duplication risk)
│   │   ├── author/
│   │   │   └── author.py    ← Author (orphaned)
│   │   ├── book/
│   │   │   ├── book.py      ← Book (central entity)
│   │   │   ├── book_detail.py
│   │   │   └── book_image.py
│   │   ├── category/
│   │   │   └── category.py  ← Category (orphaned)
│   │   ├── cart/
│   │   │   └── cart.py      ← Cart + CartItem
│   │   ├── customer/
│   │   │   └── customer.py
│   │   ├── inventory/
│   │   │   └── inventory.py ← Duplicates Book.stock
│   │   ├── order/
│   │   │   ├── order.py
│   │   │   ├── order_item.py
│   │   │   ├── payment.py
│   │   │   └── shipping.py
│   │   ├── rating/
│   │   │   └── rating.py    ← Rating + Comment
│   │   ├── recommendation/
│   │   │   └── recommendation.py ← M:M with Book
│   │   └── staff/
│   │       └── staff.py
│   ├── controllers/
│   │   ├── api_views.py     ← JSON endpoints (security issues)
│   │   ├── bookController/
│   │   │   ├── views.py     ← Book browsing
│   │   │   ├── cart_views.py
│   │   │   ├── rating_comment_views.py
│   │   │   └── recommendation_views.py
│   │   ├── orderController/
│   │   │   ├── views.py
│   │   │   ├── checkout_views.py
│   │   │   └── payment_shipping_views.py
│   │   ├── customerController/
│   │   │   └── views.py     ← Auth + dashboard
│   │   └── staffController/
│   │       └── views.py     ← 1 page, no auth
│   ├── services/
│   │   ├── payment_shipping_service.py ← PaymentService, ShippingService
│   │   └── recommendation.py ← Simple recommend_books() function
│   ├── urls/
│   │   ├── book_urls.py
│   │   ├── order_urls.py
│   │   ├── customer_urls.py
│   │   └── staff_urls.py
│   ├── templates/
│   ├── static/
│   ├── management/
│   │   └── commands/
│   │       └── populate_books.py ← Data seeding command
│   ├── migrations/
│   ├── tests.py
│   ├── tests_orders.py
│   ├── tests_payment_shipping.py
│   ├── tests_rating_comment.py
│   └── notes.txt
├── tools/
│   └── extract_pdf.py       ← Data import script
├── manage.py
└── db.sqlite3               ← Development database
```

---

**End of Analysis**
