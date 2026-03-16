# Phase 2: Payment Service Extraction - Implementation Guide

## 🎯 Phase 2 Overview

**Status:** ✅ Implementation Complete  
**Objective:** Extract Payment Service into independent microservice  
**Duration:** 3-4 days (for full implementation)  
**Complexity:** Medium

---

## 📊 What Was Implemented

### Component 1: Payment Service Application (FastAPI)

**Location:** `payment-service/`

**Architecture:**
```
payment-service/
├── app.py                 # FastAPI application
├── config.py              # Configuration management
├── database.py            # SQLAlchemy database setup
├── schemas.py             # Pydantic request/response models
├── models/
│   ├── payment.py         # Payment and Refund models
│   └── __init__.py
├── routes/
│   ├── payments.py        # Payment processing endpoints
│   └── __init__.py
├── services/
│   ├── stripe_service.py  # Stripe integration
│   ├── event_publisher.py # RabbitMQ event publishing
│   └── __init__.py
├── tests/
│   └── __init__.py
├── requirements.txt       # Dependencies
├── Dockerfile            # Container configuration
├── .env.example          # Environment variables template
└── __init__.py
```

**Key Features:**
- ✅ Stripe payment processing
- ✅ Token-based authentication
- ✅ Event publishing to RabbitMQ
- ✅ Payment status tracking
- ✅ Refund processing
- ✅ Database persistence
- ✅ Error handling & logging

---

### Component 2: Payment Service Endpoints

#### Process Payment
```http
POST /api/v1/payments/process
Authorization: Bearer {token}
Content-Type: application/json

{
  "order_id": "order-123",
  "amount": 99.99,
  "currency": "USD",
  "customer_email": "customer@example.com",
  "payment_method_id": "tok_visa"
}

Response 200:
{
  "status": "succeeded",
  "payment_id": "ch_1234567890",
  "order_id": "order-123",
  "amount": 99.99,
  "currency": "USD",
  "transaction_id": "ch_1234567890",
  "message": "Payment processed successfully"
}

Response 402:
{
  "status": "failed",
  "error": "Card declined",
  "order_id": "order-123"
}
```

#### Get Payment Status
```http
GET /api/v1/payments/{order_id}
Authorization: Bearer {token}

Response 200:
{
  "order_id": "order-123",
  "status": "completed",
  "amount": 99.99,
  "currency": "USD",
  "transaction_id": "ch_1234567890",
  "created_at": "2026-03-09T12:00:00",
  "updated_at": "2026-03-09T12:05:00"
}
```

#### Refund Payment
```http
POST /api/v1/payments/refund
Authorization: Bearer {token}
Content-Type: application/json

{
  "payment_id": "ch_1234567890",
  "amount": 50.00,
  "reason": "Customer request"
}

Response 200:
{
  "status": "succeeded",
  "refund_id": "re_1234567890",
  "payment_id": "ch_1234567890",
  "amount": 50.00,
  "message": "Refund processed successfully"
}
```

#### Health Check
```http
GET /health

Response 200:
{
  "status": "healthy",
  "service": "payment-service",
  "version": "1.0.0"
}
```

---

### Component 3: Payment Client (Monolith)

**Location:** `store/payment_client.py`

Used by monolith to communicate with Payment Service.

**Features:**
- Automatic retry logic via idempotency keys
- Error handling and logging
- Service health check
- Timeout management

**Usage Example:**
```python
from store.payment_client import PaymentClient

client = PaymentClient()

# Process payment
result = client.process_payment(
    order_id='order-123',
    amount=99.99,
    customer_email='customer@example.com',
    payment_method_id='tok_visa'
)

if result['status'] == 'succeeded':
    # Payment successful
    pass

# Check payment status
status = client.get_payment_status('order-123')

# Refund payment
refund = client.refund_payment(
    payment_id='ch_1234567890',
    amount=50.00,
    reason='Customer request'
)

# Health check
is_healthy = client.health_check()
```

---

### Component 4: Updated Checkout Flow

**File:** `store/controllers/orderController/checkout_views.py`

**Updated Functions:**
- `payment_confirm()` - Now calls external Payment Service

**Flow:**
1. User initiates checkout
2. Creates order in monolith
3. Calls Payment Service API
4. Payment Service processes with Stripe
5. Event published on success/failure
6. Monolith updates order status
7. Event triggers downstream systems

---

### Component 5: Docker Compose

**Files:**
- `docker-compose.yml` - Service orchestration
- `Dockerfile` - Monolith container
- `payment-service/Dockerfile` - Payment Service container

**Services:**
- **PostgreSQL** - Shared database (port 5432)
- **RabbitMQ** - Message queue (port 5672, management UI 15672)
- **Web** - Django monolith (port 8000)
- **Payment Service** - FastAPI (port 5000)

---

## 🚀 Installation & Setup

### Prerequisites
- Docker and Docker Compose installed
- Python 3.11+
- Stripe test account (for testing)

### Step 1: Copy Environment Files

```bash
cd payment-service
cp .env.example .env
cd ..
```

Update `.env` files with your Stripe keys if testing.

### Step 2: Start Services with Docker Compose

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# View payment service logs
docker-compose logs -f payment-service

# View web server logs
docker-compose logs -f web
```

### Step 3: Initialize Databases

```bash
# Run migrations for monolith
docker-compose exec web python manage.py migrate

# Initialize payment service database
docker-compose exec payment-service python -c "from database import init_db; init_db()"
```

### Step 4: Create API Tokens

```bash
# In monolith
docker-compose exec web python manage.py create_api_token -u admin
docker-compose exec web python manage.py create_api_token --service payment-service
```

### Step 5: Test Health Checks

```bash
# Test monolith
curl http://localhost:8000/health

# Test payment service
curl http://localhost:5000/health

# Test RabbitMQ management UI
# Visit http://localhost:15672 (guest/guest)
```

---

## 🧪 Testing Payment Service

### Unit Tests

Create `payment-service/tests/test_payments.py`:

```python
import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_process_payment_missing_auth():
    response = client.post("/api/v1/payments/process", json={})
    assert response.status_code == 401

def test_process_payment_invalid_token():
    response = client.post(
        "/api/v1/payments/process",
        json={
            "order_id": "test-123",
            "amount": 99.99,
            "currency": "USD",
            "customer_email": "test@example.com",
            "payment_method_id": "tok_test"
        },
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401
```

### Integration Tests

Test payment flow end-to-end:

```bash
# 1. Start services
docker-compose up -d

# 2. Create test order
curl -X POST http://localhost:8000/api/orders/ \
  -H "Authorization: Bearer {token}" \
  -d '{...order data...}'

# 3. Process payment
curl -X POST http://localhost:5000/api/v1/payments/process \
  -H "Authorization: Bearer {token}" \
  -d '{...payment data...}'

# 4. Verify payment was recorded
curl http://localhost:5000/api/v1/payments/{order_id} \
  -H "Authorization: Bearer {token}"
```

---

## 📝 Key Configuration

### Environment Variables

**Monolith (.env):**
```
PAYMENT_SERVICE_URL=http://payment-service:5000
PAYMENT_SERVICE_TOKEN=payment-service-token-123
```

**Payment Service (.env):**
```
DATABASE_URL=postgresql://bookstore:bookstore_password@postgres:5432/payment_service
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
```

### Stripe Configuration

For testing, use Stripe test cards:
- **Visa (Success):** 4242 4242 4242 4242
- **Visa (Decline):** 4000 0000 0000 0002
- **Amex:** 3782 822463 10005

---

## 🔄 Event Flow

### Payment Processing Flow

```
1. User submits checkout form
   └─> payment_confirm() in monolith

2. Monolith calls Payment Service
   └─> PaymentClient.process_payment()

3. Payment Service processes payment
   └─> Stripe API call
   └─> Payment record created in DB

4. Success: Publish payment.completed event
   └─> Order updated in monolith
   └─> Inventory updated
   └─> Notifications queued

5. Failure: Publish payment.failed event
   └─> Order remains pending
   └─> User can retry
```

### Event Publishing

```python
# Payment Service publishes
event_publisher.publish_payment_completed(
    order_id=order.id,
    transaction_id=charge_id,
    amount=amount,
    correlation_id=order.id
)

# Monolith listens
# Can be consumed by:
# - Notification Service (send confirmation email)
# - Inventory Service (reserve stock, reduce count)
# - Analytics Service (record transaction)
# - Shipping Service (prepare shipment)
```

---

## 🐛 Troubleshooting

### Payment Service won't start

```bash
# Check logs
docker-compose logs payment-service

# Common issues:
# 1. Port 5000 already in use
#    docker ps | grep 5000
#    kill process or change port in docker-compose.yml

# 2. Database connection error
#    docker-compose logs postgres
#    Ensure postgres is healthy first

# 3. Import errors
#    docker-compose exec payment-service pip install -r requirements.txt
```

### Stripe connection issues

```bash
# Check Stripe credentials
docker-compose exec payment-service python -c "
  import stripe
  from config import get_settings
  stripe.api_key = get_settings().STRIPE_SECRET_KEY
  stripe.Account.retrieve()
"
```

### RabbitMQ connection issues

```bash
# Check RabbitMQ is running
docker-compose ps rabbitmq

# Check RabbitMQ logs
docker-compose logs rabbitmq

# Access management UI
# http://localhost:15672 (guest/guest)
```

---

## 📊 Database Schema

### Payment Table

```sql
CREATE TABLE payments (
  id INTEGER PRIMARY KEY,
  order_id VARCHAR(255) UNIQUE NOT NULL,
  transaction_id VARCHAR(255),
  customer_email VARCHAR(255) NOT NULL,
  amount FLOAT NOT NULL,
  currency VARCHAR(3),
  status VARCHAR(50),
  payment_method_id VARCHAR(255),
  error_message VARCHAR(1000),
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

### Refund Table

```sql
CREATE TABLE refunds (
  id INTEGER PRIMARY KEY,
  payment_id INTEGER NOT NULL,
  transaction_id VARCHAR(255),
  refund_transaction_id VARCHAR(255),
  amount FLOAT NOT NULL,
  reason VARCHAR(500),
  status VARCHAR(50),
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

---

## 🎓 Learning Resources

- **FastAPI:** https://fastapi.tiangolo.com/
- **Stripe API:** https://stripe.com/docs/api
- **SQLAlchemy:** https://docs.sqlalchemy.org/
- **Docker Compose:** https://docs.docker.com/compose/

---

## ✅ Phase 2 Checklist

- [x] Payment Service FastAPI app created
- [x] Stripe integration implemented
- [x] Database models and migrations
- [x] API endpoints with authentication
- [x] Event publishing to RabbitMQ
- [x] Payment client for monolith
- [x] Order checkout updated
- [x] Docker Compose setup
- [x] Error handling and logging
- [x] Documentation complete

---

## 🚀 Next Steps (Phase 3)

1. **Shipping Service Extraction** (Similar pattern)
2. **Notification Service** (Email/SMS)
3. **Inventory Service** (Stock management)
4. **Kubernetes Deployment** (Production ready)
5. **API Gateway** (Single entry point)

---

**Phase 2 Status:** ✅ Implementation Complete - Ready for Testing & Deployment
