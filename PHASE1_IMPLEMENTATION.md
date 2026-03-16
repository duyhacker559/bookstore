# Phase 1: Foundation Setup - Complete Implementation Guide

This document details all the changes made to implement Phase 1 of the microservices transformation.

## 📋 Phase 1 Components Implemented

### ✅ Component 1: Data Model Fixes

**Problem:** Duplicate inventory management (Book.stock + Inventory.quantity)

**Solution:** 
- Created migration `0007_consolidate_inventory.py` that:
  - Creates Inventory records for all Books if missing
  - Syncs quantities from Book.stock to Inventory.quantity
  - Provides data consolidation script with logging

**Files:**
- `store/migrations/0007_consolidate_inventory.py` - NEW

**How it works:**
```bash
python manage.py migrate
# Output: 
# [CONSOLIDATE] Book 1 (Python Guide): Book.stock=50, Inventory.quantity=45 -> using Book.stock
# [CREATE] Inventory for Book 2 (Django Book): quantity=30
```

---

### ✅ Component 2: Author/Category ForeignKey Linking

**Problem:** Author and Category not linked to Book (using string fields instead)

**Solution:**
- Added `author_fk` and `category_fk` ForeignKey fields to Book model
- Created migration `0008_book_add_author_category_fk.py` that:
  - Adds new FK fields
  - Auto-links existing Author/Category records by name
  - Keeps legacy string fields for backward compatibility

**Files:**
- `store/models/book/book.py` - MODIFIED
- `store/migrations/0008_book_add_author_category_fk.py` - NEW

**Model changes:**
```python
class Book(models.Model):
    # Legacy fields (kept for compatibility)
    author = models.CharField(max_length=255)  # "John Smith"
    category = models.CharField(max_length=100)  # "Fiction"
    
    # New ForeignKey fields (for microservices)
    author_fk = models.ForeignKey('Author', on_delete=SET_NULL, null=True)
    category_fk = models.ForeignKey('Category', on_delete=SET_NULL, null=True)
```

---

### ✅ Component 3: API Authentication (Django REST Framework)

**Problem:** All API endpoints are publicly accessible (security risk)

**Solution:**
- Installed Django REST Framework
- Added TokenAuthentication to all API endpoints
- Created authentication utilities (`store/auth.py`)
- Protected all existing API views with `@require_api_auth` decorator

**Files:**
- `store/auth.py` - NEW
- `store/controllers/api_views.py` - MODIFIED
- `bookstore/settings.py` - MODIFIED
- `requirements.txt` - NEW

**How authentication works:**

1. **Get a token:**
   ```bash
   python manage.py create_api_token -u john
   # Output: Token: abc123def456...
   ```

2. **Use token in API request:**
   ```bash
   curl -H "Authorization: Bearer abc123def456..." \
        http://localhost:8000/api/books/
   ```

3. **Request without token:**
   ```bash
   curl http://localhost:8000/api/books/
   # Response: 401 Unauthorized
   ```

**Settings changes:**
```python
# bookstore/settings.py
INSTALLED_APPS = [
    ...
    'rest_framework',
    'rest_framework.authtoken',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
```

---

### ✅ Component 4: Event Bus for Microservices

**Problem:** Need async communication between monolith and microservices

**Solution:**
- Created `store/events.py` with EventBus class
- Supports RabbitMQ for production
- Falls back to logging if RabbitMQ unavailable
- Provides simple `publish_event()` function

**Files:**
- `store/events.py` - NEW

**Supported events:**
```python
# Event types that can be published
'order.created'
'order.paid'
'order.shipped'
'order.cancelled'
'payment.completed'
'inventory.reserved'
'inventory.released'
'notification.send_email'
```

**Usage:**
```python
from store.events import publish_event

# When order is created
publish_event('order.created', {
    'order_id': order.id,
    'customer_id': order.customer.id,
    'total': order.total_price,
    'correlation_id': request.id  # for tracing
})

# When payment succeeds
publish_event('payment.completed', {
    'order_id': order.id,
    'transaction_id': payment.id,
    'amount': payment.amount,
})
```

**How it works:**

1. **Development (without RabbitMQ):**
   - Events are logged to console/file
   - No RabbitMQ required
   - Perfect for testing

2. **Production (with RabbitMQ):**
   - Events published to RabbitMQ message queue
   - Microservices subscribe to specific events
   - Async, reliable communication
   - Messages persisted if consumer is down

---

### ✅ Component 5: Authentication Utilities & Management Commands

**Files:**
- `store/auth.py` - NEW (authentication helpers)
- `store/management/commands/create_api_token.py` - NEW (token management)

**Management commands:**

```bash
# Create token for a user
python manage.py create_api_token -u john

# Create token for a microservice
python manage.py create_api_token --service payment-service

# List all tokens
python manage.py create_api_token --list

# Delete a token
python manage.py create_api_token --delete john
```

---

## 🚀 Installation & Setup

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

**Key packages added:**
- `djangorestframework==3.14.0` - REST API framework
- `pika==1.3.2` - RabbitMQ client
- `requests==2.31.0` - HTTP client for service calls
- `python-dotenv==1.0.0` - Environment variables

### Step 2: Run Migrations

```bash
python manage.py migrate

# Expected output:
# Operations to perform:
#   Apply all migrations: store
# Running migrations:
#   Applying store.0007_consolidate_inventory...
#   Applying store.0008_book_add_author_category_fk...
# OK
```

### Step 3: Create First API Token

```bash
python manage.py create_api_token -u admin
# Output:
# ✓ Token created for user "admin"
# Token: abc123def456xyz789...
```

### Step 4: Start RabbitMQ (Optional)

For event publishing to actually work with microservices:

```bash
# Using Docker
docker run -d --name rabbitmq \
    -p 5672:5672 \
    -p 15672:15672 \
    rabbitmq:3-management

# Visit management UI at http://localhost:15672 (guest/guest)
```

### Step 5: Create Environment Config

```bash
cp .env.example .env
# Edit .env with your settings
```

### Step 6: Run Development Server

```bash
python manage.py runserver
# Server runs at http://localhost:8000
```

---

## 🧪 Testing Phase 1

### Method 1: Automatic Setup Script

```bash
python manage.py shell < setup_phase1.py

# This will:
# 1. Verify all migrations are applied
# 2. Check DRF is installed
# 3. Create test user and token
# 4. Create service tokens for microservices
# 5. Test event publishing
# 6. Verify models have new fields
```

### Method 2: Manual Testing

**Test 1: API without authentication (should fail)**
```bash
curl http://localhost:8000/api/books/
# Response: {"error": "Missing or invalid Authorization header"}
```

**Test 2: API with valid token (should succeed)**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" \
     http://localhost:8000/api/books/
# Response: {"books": [...]}
```

**Test 3: Event publishing**
```bash
python manage.py shell
>>> from store.events import publish_event
>>> publish_event('order.created', {'order_id': '123', 'total': 99.99})
True  # Success
```

**Test 4: Database consolidation**
```bash
python manage.py shell
>>> from store.models.book.book import Book
>>> from store.models.inventory.inventory import Inventory
>>> book = Book.objects.first()
>>> print(f"Book.stock: {book.stock}")
Book.stock: 50
>>> print(f"Inventory.quantity: {book.inventory.quantity}")
Inventory.quantity: 50
```

---

## 📊 Changes Summary

| Component | Files | Status |
|-----------|-------|--------|
| Data Consolidation | 1 migration | ✅ Complete |
| Model Linking | 1 migration + model update | ✅ Complete |
| API Authentication | 2 new files + 3 modified | ✅ Complete |
| Event System | 1 new file | ✅ Complete |
| Token Management | 1 new command | ✅ Complete |
| Dependencies | requirements.txt | ✅ Complete |
| Config Template | .env.example | ✅ Complete |

---

## 🔗 How it integrates with Phase 2

### Payment Service Integration

With Phase 1 in place, the monolith can:

1. **Make authenticated calls to Payment Service**
   ```python
   import requests
   
   response = requests.post(
       f"{settings.PAYMENT_SERVICE_URL}/api/v1/payments/process",
       json={'order_id': '123', 'amount': 99.99},
       headers={'Authorization': f'Bearer {settings.PAYMENT_SERVICE_TOKEN}'}
   )
   ```

2. **Listen for payment events from Payment Service**
   ```python
   # Payment Service publishes 'payment.completed' event
   # Monolith subscribes and updates order status
   ```

3. **Use same data model for all services**
   - Book model has ForeignKey to Author/Category
   - Inventory consolidated and reliable
   - Clear data ownership and relationships

---

## 📝 Next Steps (Phase 2)

With Phase 1 foundation ready:

1. **Create Payment Service**
   - FastAPI application
   - Stripe integration
   - Webhook handling

2. **Update checkout flow**
   - Call Payment Service API
   - Publish payment events
   - Listen for payment completion

3. **Extract Shipping Service**
   - Similar to Payment Service
   - Carrier API integration

4. **Set up Docker Compose**
   - Container for monolith
   - Container for Payment Service
   - Container for RabbitMQ
   - Shared database

---

## 🐛 Troubleshooting

### Q: Got "ModuleNotFoundError: No module named 'rest_framework'"
A: Run `pip install -r requirements.txt`

### Q: Migration fails with "table inventory does not exist"
A: Run `python manage.py migrate --fake store 0007` then `python manage.py migrate`

### Q: "Cannot connect to RabbitMQ" warning but events still work
A: RabbitMQ is optional. Events are logged instead. Install Docker to run RabbitMQ.

### Q: API returns 401 even with valid token
A: Verify token format is `Bearer {token}` (with space after Bearer)

### Q: How do I know which user a token belongs to?
A: Run `python manage.py create_api_token --list`

---

## 📚 Documentation Files

- **[MICROSERVICES_IMPLEMENTATION.md](../MICROSERVICES_IMPLEMENTATION.md)** - Phase 1-4 detailed guide
- **[.env.example](.env.example)** - Environment variables reference
- **[setup_phase1.py](setup_phase1.py)** - Automatic setup and verification script
- **[requirements.txt](requirements.txt)** - Python dependencies

---

## ✅ Phase 1 Checklist

- [x] Data model consolidation migration created
- [x] Author/Category ForeignKey fields added
- [x] Django REST Framework installed and configured
- [x] API authentication implemented and tested
- [x] Event bus system created
- [x] Management command for token generation
- [x] Requirements.txt with all dependencies
- [x] .env template for configuration
- [x] Setup verification script
- [x] Documentation complete

**Phase 1 Status: ✅ READY FOR PHASE 2**
