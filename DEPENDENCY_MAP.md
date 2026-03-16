# Bookstore Architecture - Quick Reference & Dependency Map

## Quick Model Reference

### All 16 Models at a Glance

```
┌─ AUTHENTICATION (Django Built-in)
│  └─ User (Django User model)

├─ CUSTOMER MANAGEMENT
│  ├─ Customer (1:1 with User)
│  └─ UserProfile (1:1 with User) ⚠️ DUPLICATE WITH CUSTOMER
│  └─ Staff (1:1 with User)

├─ BOOK CATALOG (5 models + relationships)
│  ├─ Book (central)
│  │  ├─ BookDetail (1:1)
│  │  ├─ BookImage (1:M)
│  │  ├─ Inventory (1:1) ⚠️ DUPLICATES Book.stock
│  │  └─ Rating (1:M) ⚠️ UPDATES Book.rating
│  ├─ Author ⚠️ ORPHANED - not linked to Book
│  └─ Category ⚠️ ORPHANED - not linked to Book

├─ CART MANAGEMENT
│  ├─ Cart (1:1 with User, cascade)
│  └─ CartItem (1:M with Cart, M:1 with Book)

├─ ORDER WORKFLOW
│  ├─ Order (M:1 with Customer)
│  ├─ OrderItem (1:M with Order, M:1 with Book)
│  │  └─ Stores snapshot of Book.price at time
│  ├─ Payment (1:1 with Order)
│  └─ Shipment (1:1 with Order)

├─ RATINGS & REVIEWS
│  ├─ Rating (M:1 with Customer, M:1 with Book)
│  │  └─ Unique constraint: (customer, book)
│  └─ Comment (M:1 with Customer, M:1 with Book)
│     ├─ Unique constraint: (customer, book)
│     ├─ FK to Rating (for grouping)
│     └─ has_purchased flag

└─ RECOMMENDATIONS
   └─ Recommendation (M:1 with User, M:M with Book)
      └─ NOT ACTUALLY USED (unused model)
```

---

## HTTP Request Flow Diagrams

### 1. Book Browsing Flow (Read-only)
```
GET / (book_list)
  │
  ├─ Query: Book.objects.all()
  ├─ Filters: title, category, price, rating, stock
  ├─ Sorting: name, price, rating
  ├─ Pagination: 12 per page
  │
  ├─ SELECT * FROM store_book
  │       WHERE title LIKE ? OR category IN (?)
  │       AND price BETWEEN ? AND ?
  │       AND rating >= ?
  │       ORDER BY ? LIMIT 12 OFFSET ?
  │
  └─ Response: Render book/list.html with page_obj
     Display: 12 books + pagination + filters

Performance: O(n) - full table scan each request
⚠️ Should add: Elasticsearch for large datasets
```

### 2. Add to Cart Flow
```
POST /add/{book_id}/ (add_to_cart)
  │
  ├─ Check: Auth required (login_required)
  │
  ├─ READ: Book by ID
  │  └─ SELECT * FROM store_book WHERE id = ?
  │
  ├─ READ/CREATE: Cart for current user
  │  └─ SELECT OR CREATE FROM store_cart WHERE user_id = ?
  │
  ├─ READ/CREATE: CartItem
  │  └─ SELECT OR CREATE FROM store_cartitem 
  │     WHERE cart_id = ? AND book_id = ?
  │
  └─ IF created:
      └─ UPDATE cartitem SET quantity = quantity + 1
      
Response: Redirect to /cart/

Database queries: 3-4 (hit create-or-get twice)
⚠️ Race condition: Two concurrent requests → quantity not incremented correctly
```

### 3. Checkout Flow (CRITICAL)
```
POST /checkout/ (checkout)
  │
  ├─ Check: Auth + non-empty cart
  │
  ├─ READ: Cart + CartItems with Books
  │  └─ SELECT cart, cartitem, book (JOIN)
  │
  ├─ READ/CREATE: Customer profile
  │  └─ SELECT OR CREATE customer WHERE user_id = ?
  │
  ├─ CREATE: Order
  │  └─ INSERT INTO store_order 
  │     (customer_id, total_amount, status, created_at)
  │
  ├─ CREATE: OrderItems (loop for each cart item)
  │  └─ INSERT INTO store_orderitem × N
  │     (order_id, book_id, quantity, price)
  │
  ├─ UPDATE: Reduce Book.stock
  │  └─ UPDATE store_book SET stock = stock - ?
  │     WHERE id = ? (× N times)
  │
  ├─ CREATE: Shipment (via ShippingService)
  │  └─ INSERT INTO store_shipment
  │     (order_id, address, fee, status, method_name)
  │
  ├─ DELETE: Cart items
  │  └─ DELETE FROM store_cartitem WHERE cart_id = ?
  │
  └─ Response: Redirect to /payment/initiate/{order_id}/

Database operations: 4 + N writes
⚠️ RISKS:
  - If write fails midway, inconsistent state
  - Book.stock reduced even if payment fails
  - No transaction boundaries visible
  - Race condition: Two users buying last book
```

### 4. Payment Flow
```
POST /payment/{order_id}/ (payment_confirm)
  │
  ├─ Check: Auth + order ownership
  │
  ├─ READ: Order by ID
  │
  ├─ CREATE: Payment record
  │  └─ INSERT INTO store_payment
  │     (order_id, method_name, amount, status='Pending')
  │
  ├─ PROCESS: PaymentService.process_payment()
  │  └─ status = 'Completed' (always succeeds in demo)
  │
  ├─ UPDATE: Order status
  │  └─ UPDATE store_order SET status = 'Paid'
  │
  ├─ DELETE: Cart items
  │  └─ DELETE FROM store_cartitem WHERE user_id = ?
  │
  └─ Response: Success page

⚠️ CRITICAL ISSUES:
  - No actual payment integration
  - Payment always succeeds
  - No error handling
  - No idempotency (double-charge risk)
  - No webhook mechanism for async updates
```

### 5. Rating & Review Flow
```
POST /{book_id}/rate/ (add_rating_comment)
  │
  ├─ Check: Auth required
  │
  ├─ READ: Book, Customer (from User)
  │
  ├─ VERIFY: Check if customer purchased this book
  │  └─ SELECT EXISTS(SELECT 1 FROM store_orderitem
  │     WHERE order__customer_id = ? AND book_id = ?)
  │
  ├─ CREATE/UPDATE: Rating record
  │  └─ Rating.objects.update_or_create(
  │     customer=customer, book=book,
  │     defaults={'score': int(score)})
  │
  ├─ CREATE/UPDATE: Comment record
  │  └─ Comment.objects.update_or_create(
  │     customer=customer, book=book,
  │     defaults={'rating': rating, 'title': title, ...})
  │
  ├─ RECALCULATE: Book rating aggregate
  │  ├─ Avg = Rating.objects.filter(book=book).aggregate(Avg('score'))
  │  ├─ Count = Comment.objects.filter(book=book).count()
  │  └─ UPDATE store_book SET rating = ?, review_count = ?
  │
  └─ Response: Redirect to book detail

Database queries: 6-7 (aggregation functions)
⚠️ ISSUES:
  - Rating aggregate happens synchronously (slow)
  - If rating deleted, aggregate not recalculated
  - Denormalization creates consistency issues
√ SOLUTION: Make aggregation async (Celery task)
```

---

## Database Dependency Graph

```
Django User (required)
  ↓
  ├──→ Customer (1:1) ←── Order ←── OrderItem ←── Book
  │
  ├──→ Cart (1:1) ←── CartItem ←── Book
  │
  ├──→ UserProfile (1:1)
  │
  ├──→ Staff (1:1)
  │
  └──→ Recommendation (1:M) ←─ [M:M] ─→ Book

Book (central hub)
  ├──→ BookDetail (1:1)
  ├──→ BookImage (1:M)
  ├──→ Inventory (1:1) ⚠️ DUPLICATE with Book.stock
  ├──────→ OrderItem (1:M) ← Order ← Customer
  ├──────→ Rating (1:M) ← Customer
  │          └──→ Comment (1:M) ← Customer
  │
  ├── Author (field: CharField) ⚠️ ORPHANED
  │    └── Author model exists but not used
  │
  └── Category (field: CharField) ⚠️ ORPHANED
       └── Category model exists but not used

Order (workflow hub)
  ├──→ OrderItem (1:M) ──→ Book
  ├──→ Payment (1:1)
  ├──→ Shipment (1:1)
  └──→ Customer (M:1)
```

---

## API Endpoint Dependency Tree

### Unauthenticated Endpoints
```
GET / (book_list)
  └─ Reads: Book

GET /{book_id}/ (book_detail)
  └─ Reads: Book

GET /api/books/ (book_list_api)
  └─ Reads: Book

GET /api/books/{book_id}/ (book_detail_api)
  └─ Reads: Book

GET /api/books/{book_id}/ratings/ (get_ratings_api)
  └─ Reads: Rating, Comment, Book

GET /{book_id}/reviews/ (book_reviews)
  └─ Reads: Rating, Comment

GET /api/authors/ (author_list_api)
  └─ Reads: Author ⚠️ Not linked to Book

GET /api/authors/{author_id}/ (author_detail_api)
  └─ Reads: Author

POST /comment/{comment_id}/helpful/ (mark_helpful)
  └─ Writes: Comment.helpful_count ⚠️ NO AUTH CHECK
```

### Authenticated Endpoints
```
POST /add/{book_id}/ (add_to_cart)
  ├─ Auth: login_required
  ├─ Reads: Book, Cart, CartItem
  └─ Writes: CartItem

POST /remove/{book_id}/ (remove_from_cart)
  ├─ Auth: login_required
  ├─ Reads: Cart
  └─ Writes: Delete CartItem

GET /cart/ (cart_view)
  ├─ Auth: Optional
  ├─ Reads: Cart, CartItem, Book
  └─ Calculates: Total

GET/POST /checkout/ (checkout)
  ├─ Auth: login_required
  ├─ Reads: Cart, CartItem, Book, Customer
  ├─ Writes: Order, OrderItem, Shipment, Book.stock
  └─ Deletes: CartItem

POST /{book_id}/rate/ (add_rating_comment)
  ├─ Auth: login_required
  ├─ Reads: Book, Customer, OrderItem (verify purchase)
  ├─ Writes: Rating, Comment
  └─ Updates: Book.rating, Book.review_count

GET /recommendations/ (data_model_recommendation)
  ├─ Auth: login_required
  ├─ Reads: Book (random sample)
  └─ Note: Just returns random, not personalized

GET /customer/profile/ (customer_home)
  ├─ Auth: login_required
  ├─ Reads: Customer, Order, OrderItem
  └─ Filters: status, date range, pagination

PUT /customer/login/ (login_view)
POST /customer/register/ (register)
GET /customer/logout/ (logout_view)
  └─ Django auth views
```

---

## Module Interdependencies

### Model Imports Chain
```
models/__init__.py imports:
  ├─ models/book/book.py
  │   └─ (no dependencies)
  │
  ├─ models/book/book_detail.py
  │   └─ → book.Book
  │
  ├─ models/book/book_image.py
  │   └─ → book.Book
  │
  ├─ models/inventory/inventory.py
  │   └─ → book.Book
  │
  ├─ models/author/author.py
  │   └─ (no dependencies, orphaned)
  │
  ├─ models/category/category.py
  │   └─ (no dependencies, orphaned)
  │
  ├─ models/customer/customer.py
  │   └─ → Django settings.AUTH_USER_MODEL
  │
  ├─ models/cart/cart.py
  │   ├─ → Django settings.AUTH_USER_MODEL
  │   └─ → book.Book
  │
  ├─ models/order/order.py
  │   ├─ → book.Book
  │   └─ → customer.Customer
  │
  ├─ models/order/order_item.py
  │   ├─ → order.Order
  │   └─ → book.Book
  │
  ├─ models/order/payment.py
  │   └─ → order.Order
  │
  ├─ models/order/shipping.py
  │   └─ → order.Order
  │
  ├─ models/rating/rating.py
  │   ├─ → customer.Customer
  │   └─ → book.Book
  │
  ├─ models/recommendation/recommendation.py
  │   ├─ → Django settings.AUTH_USER_MODEL
  │   └─ → book.Book (M:M)
  │
  └─ models/user_profile.py
      └─ → Django settings.AUTH_USER_MODEL
```

### View Imports Chain
```
controllers/bookController/views.py
  └─ book.Book, Q (django ORM)

controllers/bookController/cart_views.py
  ├─ book.Book
  ├─ cart.Cart, CartItem
  └─ (optional) login_required

controllers/bookController/rating_comment_views.py
  ├─ book.Book
  ├─ customer.Customer
  ├─ rating.Rating, Comment
  ├─ OrderItem (to verify purchase)
  ├─ Avg, Q (django ORM)
  └─ login_required

controllers/orderController/checkout_views.py
  ├─ book.Book
  ├─ cart.Cart, CartItem
  ├─ customer.Customer
  ├─ order.Order, OrderItem
  ├─ payment.Payment
  ├─ shipment.Shipment
  ├─ ShippingService, PaymentService
  └─ login_required

controllers/orderController/payment_shipping_views.py
  ├─ order.Order
  ├─ payment.Payment
  ├─ shipment.Shipment
  ├─ PaymentService, ShippingService
  └─ login_required

controllers/customerController/views.py
  ├─ customer.Customer
  ├─ order.Order, OrderItem
  ├─ UserCreationForm, AuthenticationForm (Django)
  └─ login, authenticate, logout (Django auth)

controllers/api_views.py
  ├─ book.Book
  ├─ author.Author
  └─ model_to_dict (Django)
```

### Service Dependencies
```
services/payment_shipping_service.py
  ├─ payment.Payment (model)
  ├─ shipment.Shipment (model)
  └─ Decimal (from decimal)

services/recommendation.py
  └─ book.Book (model)
```

---

## Strong Coupling Points (Top 5)

### 1. 🔴 Order Process (Cannot Extract)
```
Order → requires → OrderItem
         requires → Payment
         requires → Shipment
         requires → Customer → User

If you extract:
  ✗ Order creation fails
  ✗ Payment service needs Order model
  ✗ Shipping service needs Order model
  ✗ All sync through database writes

Must stay monolithic
```

### 2. 🔴 Book → Rating Denormalization
```
User submits rating
  ↓
Rating row created
  ↓
Synchronous calc: book.rating = AVG(rating.score)
  ↓
book.review_count = COUNT(comments)
  ↓
Book model updated

Problem:
  ✗ If rating deleted, aggregates not recalculated
  ✗ If calculation fails, data corruption
  ✗ Creating rating blocks response

Solution: Async task
  Book rating update → Celery task
  Comment count → Celery task
  No response delay
```

### 3. 🔴 Cart → Order → Payment
```
Cart (ephemeral, user session)
  ↓
POST /checkout → Order creation
  ↓ (cart deleted here)
  ↓
POST /payment → Payment processing
  ↓
Cart already gone - can't recover

If payment fails:
  Cart is gone
  Can't resume checkout
  No cart history

Solution: Decouple cart lifecycle
  Don't delete cart on order
  Mark items as "in order"
  Allow recovery
```

### 4. 🔴 Stock Management (Book.stock)
```
Book.stock = actual stock
Inventory.stock = duplicate field (unused)

On checkout:
  book.stock -= quantity
  
Problems:
  ✗ Race condition: Two concurrent checkouts
  ✗ No transaction isolation
  ✗ No inventory reservations
  ✗ Inventory model not used

Solution: Inventory Service
  Reserve stock before checkout
  Confirm on payment success
  Auto-release on timeout
```

### 5. 🟡 Customer ↔ Django User
```
Customer tied to User (1:1)
User creation required for cart/order

If you extract Customer Service:
  ✗ Still need Django User for auth
  ✗ Customer profile tied to User
  ✗ Can't decouple without major refactor

Must keep User model in main monolith
```

---

## Technology Stack

```
Backend:
├─ Django 5.2.10
├─ Python 3.x
├─ SQLite (dev) / PostgreSQL (prod expected)
└─ No async workers (Celery not installed)

Frontend:
├─ Django Templates
├─ HTML/CSS/JavaScript (no modern JS framework)
└─ Bootstrap (likely)

Missing:
├─ ❌ Task queue (Celery/RQ)
├─ ❌ Cache (Redis/Memcached)
├─ ❌ Search engine (Elasticsearch)
├─ ❌ Real payment gateway
├─ ❌ Real shipping integration
├─ ❌ Email service
├─ ❌ Message broker
└─ ❌ Monitoring/logging (ELK/Datadog)

Security:
├─ Django CSRF protection
├─ Django CORS (not configured)
├─ No rate limiting
├─ No API authentication
└─ No encryption for sensitive data
```

---

## File Statistics

```
Total Models: 16
├─ Fully utilized: 11 (Book, Order, OrderItem, Payment, etc.)
├─ Partially used: 2 (Recommendation, Staff)
└─ Orphaned: 3 (Author, Category, Inventory)

Total Views/Controllers: 30+
├─ Public views: 8
├─ Authenticated views: 18
├─ Admin views: 1
└─ Staff views: 1

API Endpoints: 18
├─ JSON: 7
├─ HTML: 11
└─ Without auth: 9 ⚠️ SECURITY RISK

Database Queries:
├─ Per book_list request: ~20 queries
├─ Per checkout request: ~8 queries
├─ Per rating submit: ~7 queries
└─ Risk: N+1 queries throughout

Lines of Code:
├─ Models: ~500
├─ Views: ~2000
├─ URLs: ~100
├─ Services: ~150
├─ Templates: ~1000 (estimated)
└─ Total: ~3750 (excluding tests)
```

---

**Doc generated: March 9, 2026**
