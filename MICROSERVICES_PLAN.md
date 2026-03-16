# Bookstore Architecture - Microservices Extraction Plan

## Quick Reference: What Can Be Extracted

### ✅ EASY TO EXTRACT (Low Risk, High Value)

#### 1. Payment Gateway Service
```
Current: PaymentService (Django)
Extract: Separate HTTP microservice

Implementation:
├─ Technology: Node.js + Stripe SDK / Python + Flask
├─ Database: PostgreSQL (separate from main DB)
├─ Communication: REST API
├─ Transactions: 
│  └─ Order DB → Payment Service → Webhook → Update Order status
├─ Scaling: Independent horizontal scaling
└─ Risk Level: 🟡 MEDIUM (Must handle transaction failures)

Interface:
  POST /payments
    ├─ Input: {order_id, amount, method, token}
    ├─ Output: {payment_id, status, reference}
    └─ Status: pending|completed|failed|refunded

  GET /payments/{payment_id}
    └─ Output: Payment details with timestamps

  POST /payments/{payment_id}/refund
    └─ Initiates refund process

Benefits:
  ✓ Scales independently
  ✓ Can use different tech stack
  ✓ Easier to test with third-party APIs
  ✓ Can integrate multiple gateways
  ✓ Audit trail separate from main DB
```

#### 2. Shipping Service
```
Current: ShippingService (Django)
Extract: Separate HTTP microservice

Implementation:
├─ Technology: Node.js + EasyPost / Python + shippo
├─ Database: PostgreSQL (tracking history)
├─ APIs: Integrate FedEx, UPS, USPS, DHL
├─ Features:
│  ├─ Rate shopping across carriers
│  ├─ Real-time tracking updates
│  ├─ Label PDF generation
│  └─ Address validation
└─ Risk Level: 🟡 MEDIUM (Carrier API failures, address validation)

Interface:
  POST /shipments
    ├─ Input: {order_id, address, weight, carrier, speed}
    ├─ Output: {shipment_id, tracking_number, label_url, fee}
    └─ Validates address with USPS/UPU API

  GET /shipments/{shipment_id}/track
    ├─ Output: {status, last_update, location, estimated_delivery}
    └─ Polls carrier APIs in background

  POST /shipments/{shipment_id}/cancel
    └─ Attempts to cancel before carrier pickup

Webhook to main service:
  shipment.status_updated → POST /webhooks/shipment
    └─ Updates Order.status

Benefits:
  ✓ Decouples from order processing
  ✓ Can batch carrier API calls
  ✓ Real-time tracking without polling
  ✓ Easier to add new carriers
  ✓ Historical tracking data archived
```

#### 3. Notification Service
```
Current: NOT IMPLEMENTED
Extract: Separate notification queue service

Implementation:
├─ Technology: Python + Celery + Redis
├─ Queue: RabbitMQ or Redis
├─ Channels: Email (SendGrid), SMS (Twilio), Push (FCM)
├─ Database: PostgreSQL (audit log)
└─ Risk Level: 🟢 LOW (Notifications are non-critical)

Architecture:
  ┌─ Event Stream (Redis/Kafka)
  │
  Order Service publishes:
  ├─ order.created          → Welcome email + SMS
  ├─ payment.completed      → Receipt
  ├─ shipment.shipped       → Tracking link + SMS
  └─ delivery.confirmed     → Review request

  Notification Service subscribes:
  ├─ Reads from event stream
  ├─ Renders templates
  ├─ Sends via providers
  └─ Logs delivery status

Interface:
  POST /notifications/send
    └─ {template_id, recipient_id, variables}

  GET /notifications/history/{customer_id}
    └─ All notifications sent to customer

Benefits:
  ✓ Scales independently
  ✓ Can retry failed sends
  ✓ Audit trail of all communications
  ✓ A/B testing on templates
  ✓ Easy to add new channels (Slack, Telegram)
```

---

### 🟡 MEDIUM EFFORT (Moderate Risk, High Value)

#### 4. Recommendation Engine
```
Current: Just returns random books
Extract: Separate ML microservice

Implementation:
├─ Technology: Python + scikit-learn / TensorFlow
├─ Database: None (Redis cache for results)
├─ Training: Batch job (nightly)
├─ Features:
│  ├─ Collaborative filtering (user-user, item-item)
│  ├─ Content-based filtering (genres, authors)
│  ├─ Hybrid approach
│  └─ A/B testing framework
└─ Risk Level: 🟢 LOW (Wrong recommendations won't break system)

Data inputs:
  ├─ Purchase history (OrderItem)
  ├─ Ratings (Rating model)
  ├─ Browse history (if tracked)
  ├─ Time spent on book pages (if tracked)
  └─ Social signals (if available)

Interface:
  GET /recommendations
    ├─ Query: {user_id, count=5, context=category|trending|personalized}
    └─ Output: [{book_id, score, reason}]

  POST /feedback
    ├─ Input: {user_id, book_id, action=purchased|rated|ignored}
    └─ Updates training data

Training pipeline:
  1. Daily: Fetch all user interactions
  2. Build recommendation matrix
  3. Cache top recommendations per user
  4. Deploy new model

Benefits:
  ✓ Can use expensive algorithms
  ✓ Independent scaling
  ✓ A/B test different algorithms
  ✓ Real-time feedback integration
  ✓ Can be replaced without main app restart
```

#### 5. Reviews & Ratings Service
```
Current: Tightly coupled to Book model
Extract: Separate service with async aggregation

Implementation:
├─ Technology: Python + Flask
├─ Database: MongoDB (schema-flexible) or PostgreSQL
├─ Features:
│  ├─ Review moderation workflow
│  ├─ Spam detection
│  ├─ Helpful voting
│  └─ Keyword extraction
└─ Risk Level: 🟡 MEDIUM (Denormalized Book.rating needs sync)

Architecture:
  Order Service creates OrderItem
  ↓
  Reviews Service subscribes to "item_purchased" event
  ↓
  User can now rate/review that book
  ↓
  Review saved in Reviews Service DB
  ↓
  Async job: Recalculate Book.rating
  ↓
  Event: "review.aggregated" → Update main Book DB (eventually consistent)

Database schema (Reviews Service):
  Reviews:
    ├─ id
    ├─ book_id (denormalized, not FK)
    ├─ user_id (denormalized)
    ├─ rating (1-5)
    ├─ title
    ├─ content
    ├─ is_verified_purchase
    ├─ helpful_yes
    ├─ helpful_no
    ├─ created_at
    └─ updated_at

  Indexes:
    ├─ (book_id, created_at DESC)
    ├─ (user_id, created_at DESC)
    └─ (helpful_yes - helpful_no DESC)

Interface:
  POST /reviews/books/{book_id}
    ├─ Input: {user_id, rating, title, content}
    ├─ Output: {review_id, status}
    └─ Status: pending_moderation|published|rejected

  GET /reviews/books/{book_id}
    ├─ Query: {sort=helpful|recent, page=1, limit=20}
    └─ Output: [{review}, average_rating, rating_distribution]

  POST /reviews/{review_id}/helpful
    └─ Increments helpful_yes

  POST /reviews/{review_id}/unhelpful
    └─ Increments helpful_no

Event published:
  review.published → Recalculate Book.rating in background

Benefits:
  ✓ Reviews don't slow down book browsing
  ✓ Can implement moderation queue
  ✓ Spam detection independent
  ✓ Helpful count doesn't lock main DB
  ✓ Can search reviews separately
```

#### 6. Inventory Service
```
Current: Book.stock (single field)
Extract: Separate service with reservations

Implementation:
├─ Technology: Python + FastAPI
├─ Database: PostgreSQL (with transactions)
├─ Features:
│  ├─ Stock reservations (temporary holds)
│  ├─ Back-order management
│  ├─ Warehouse allocation
│  └─ Low-stock alerts
└─ Risk Level: 🔴 HIGH (Double-booking risk)

Key concept: Inventory Reservations
  Cart Item → Reserve stock (15 min TTL)
    ↓
  Checkout → Confirm reservation (lock it)
    ↓
  Payment failed → Release reservation
    ↓
  Cart abandoned → Auto-release after TTL

Database schema (Inventory Service):
  InventoryHold:
    ├─ id
    ├─ book_id
    ├─ user_id
    ├─ quantity
    ├─ status: reserved|confirmed|released
    ├─ created_at
    ├─ expires_at (TTL for auto-release)
    └─ released_at

  InventoryLog:
    ├─ id
    ├─ book_id
    ├─ quantity_before
    ├─ quantity_after
    ├─ reason: purchased|returns|adjustment|manual
    ├─ reference_id (order_id/return_id)
    └─ timestamp

Interface:
  POST /inventory/reserve
    ├─ Input: {book_id, quantity, user_id}
    ├─ Output: {reservation_id} or {error: "out_of_stock"}
    └─ TTL: 15 minutes (auto-expires)

  POST /inventory/confirm
    ├─ Input: {reservation_id}
    ├─ Output: {status: confirmed}
    └─ Locks the hold

  POST /inventory/release
    ├─ Input: {reservation_id}
    └─ Releases hold, restores available

  GET /inventory/books/{book_id}
    ├─ Output: {total, reserved, available}
    └─ Real-time availability

  GET /inventory/{book_id}/history?days=30
    └─ Movement history for analytics

Benefits:
  ✓ Prevents overselling
  ✓ No "add to cart then sold out" issues
  ✓ Supports multiple warehouses
  ✓ Audit trail of all movements
  ✓ Can implement low-stock notifications
```

---

### 🔴 HARD / NOT RECOMMENDED

#### ❌ DO NOT EXTRACT: Authentication Service
```
Why it's hard:
├─ All other services depend on Auth
├─ Django User model is embedded everywhere
├─ Session/JWT management complex
├─ SSO implementation steep learning curve
├─ Password reset, 2FA integration cost
└─ Risk Level: 🔴 CRITICAL (Breaking auth breaks everything)

Instead, improve within Django:
  ├─ Add email verification on signup
  ├─ Add password reset emails
  ├─ Add 2FA (TOTP)
  ├─ Add OAuth2 providers (Google, GitHub)
  ├─ Add API keys for service-to-service auth
  └─ Consider: django-oauth-toolkit for OAuth2 server
```

#### ⚠️ DEFER: Search/Catalog Service
```
Why it's complex:
├─ Book data spread across multiple models
├─ Denormalized fields (rating, review_count)
├─ Search indexes need sync logic
├─ Empty search (all books) needs pagination
└─ Risk Level: 🟡 MEDIUM (Search isn't breaking, just slow)

Only extract when:
  ├─ Data grows >100K records
  ├─ Search queries become slow
  ├─ Need Elasticsearch features (facets, autocomplete)
  └─ Multiple tenants / platforms

When extracting:
  ├─ Use Elasticsearch + sync queue
  ├─ Main DB = source of truth
  ├─ Search = secondary index
  └─ Update via event stream
```

---

## Data Migration Strategy

### Moving from Monolith to Services

**Phase 1: Stripe Payment Integration (into Django, not separate yet)**
```python
# Install: pip install stripe
# Update settings.py:
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')

# Update payment flow:
def payment_confirm(request, order_id):
    order = Order.objects.get(id=order_id)
    
    # Create Stripe payment intent
    intent = stripe.PaymentIntent.create(
        amount=int(order.total_amount * 100),  # cents
        currency='usd',
        metadata={'order_id': order_id}
    )
    
    # Save Stripe reference
    payment = Payment.objects.create(
        order=order,
        method_name='stripe',
        amount=order.total_amount,
        stripe_payment_intent_id=intent.id,
        status='pending'
    )
    
    return render(request, 'payment/stripe.html', {
        'payment_intent': intent.client_secret,
        'order': order
    })

# Webhook handler (for payment confirmation):
@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_ENDPOINT_SECRET
        )
    except:
        return HttpResponse(status=400)
    
    if event['type'] == 'payment_intent.succeeded':
        intent_id = event['data']['object']['id']
        payment = Payment.objects.get(stripe_payment_intent_id=intent_id)
        payment.status = 'completed'
        payment.save()
        payment.order.status = 'paid'
        payment.order.save()
    
    return HttpResponse(status=200)
```

**Phase 2: Extract Payment Service (if scaling needed)**
```
Move to separate service:
- Copy payment processing code to new service
- Django calls Payment Service API instead
- Keep Payment model in main DB (for history)
- Use webhook for async updates
```

---

## Integration Checklist

### For Each Extracted Service:

**Pre-Integration:**
- [ ] Service has separate database
- [ ] Service has distinct ownership/team
- [ ] Service can be deployed independently
- [ ] Service has API specification (OpenAPI/Swagger)
- [ ] Service has rate limiting
- [ ] Service has monitoring/logging (ELK/Datadog)

**Integration:**
- [ ] Main app has service discovery
- [ ] Circuit breakers for failures
- [ ] Retry logic with exponential backoff
- [ ] Event streaming setup (Kafka/RabbitMQ)
- [ ] Service-to-service authentication (mTLS/tokens)
- [ ] API gateway in front of services

**Testing:**
- [ ] Integration tests for each service
- [ ] Contract testing between services
- [ ] Chaos testing for failure scenarios
- [ ] Load testing for peak traffic

---

## Current Weaknesses Summary

### 🔴 Critical Issues

1. **Data Models**
   - Book.stock vs Inventory.quantity (duplicate)
   - Author/Category models orphaned (not linked)
   - UserProfile + Customer (duplication)
   - Book.rating denormalized (consistency risk)

2. **Security**
   - API endpoints not authenticated
   - Staff pages accessible to everyone
   - mark_helpful has no auth check
   - Demo payment processing (not real)

3. **Functionality**
   - Recommendations not implemented (just random)
   - No email notifications
   - No inventory reservations (oversell risk)
   - No order audit trail

### 🟡 High-Priority Fixes

| Fix | Effort | Impact |
|-----|--------|--------|
| Integrate real payment (Stripe) | 2-3 days | 🟢 HIGH |
| Add API authentication | 4-6 hours | 🟢 HIGH |
| Implement email notifications | 1-2 days | 🟢 HIGH |
| Fix Author/Category relationships | 2-3 days | 🟡 MEDIUM |
| Add inventory reservations | 2-3 days | 🟡 MEDIUM |
| Implement real recommendations | 2-3 days | 🟡 MEDIUM |

---

## Next Commands to Run

```bash
# 1. Create test for payment processing
python manage.py test store.tests_payment_shipping

# 2. Generate database diagram
python manage.py graph_models store -o models.png

# 3. Check for N+1 queries
pip install django-silk
# Add to INSTALLED_APPS: 'silk'
# Add to urls.py: path('silk/', include('silk.urls', namespace='silk'))

# 4. Run security check
python manage.py check --deploy

# 5. Check for missing migrations
python manage.py makemigrations --dry-run

# 6. Generate API docs
pip install drf-spectacular
# Add to INSTALLED_APPS: 'drf_spectacular'
# Add schema view to urls.py
```

---

**Last Updated: March 9, 2026**
