# Microservices Migration: Step-by-Step Implementation

## 🎯 Goal
Transform the monolithic bookstore Django app into independently deployable microservices while maintaining all existing functionality.

---

## Phase 1: Foundation (Weeks 1-2)

### Step 1: Fix Data Model Issues
**Status:** ⬜ Not Started

1. **Consolidate Inventory** - Remove duplicate Book.stock field
2. **Link Author/Category** - Add foreign keys to Book model
3. **Add Migration** - Track schema changes

**Files to modify:**
- `store/models/book/book.py` - Add author/category FK
- `store/migrations/` - New migrations

**Commands:**
```bash
python manage.py makemigrations
python manage.py migrate
```

---

### Step 2: Add API Authentication
**Status:** ⬜ Not Started

All API endpoints currently have NO authentication = SECURITY RISK

1. **Install DRF** (Django REST Framework)
   ```bash
   pip install djangorestframework
   ```

2. **Add to settings.py:**
   ```python
   INSTALLED_APPS = [
       ...
       'rest_framework',
       'rest_framework.authtoken',
   ]
   
   REST_FRAMEWORK = {
       'DEFAULT_AUTHENTICATION_CLASSES': [
           'rest_framework.authentication.TokenAuthentication',
       ],
       'DEFAULT_PERMISSION_CLASSES': [
           'rest_framework.permissions.IsAuthenticated',
       ],
   }
   ```

3. **Update API views:** Wrap with `@authentication_classes` and `@permission_classes`

4. **Generate tokens for clients:**
   ```python
   from rest_framework.authtoken.models import Token
   token = Token.objects.create(user=user)
   print(token.key)  # Share with API client
   ```

---

### Step 3: Implement Event System (Message Queue)
**Status:** ⬜ Not Started

This enables services to communicate asynchronously.

1. **Install RabbitMQ** (or Redis):
   ```bash
   # Windows: Install from https://www.rabbitmq.com/download.html
   # Or use Docker:
   docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
   ```

2. **Install pika (Python client):**
   ```bash
   pip install pika
   ```

3. **Create event publisher:**
   ```python
   # store/events.py - NEW FILE
   import pika
   import json
   
   def publish_event(exchange, routing_key, data):
       connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
       channel = connection.channel()
       channel.exchange_declare(exchange=exchange, exchange_type='topic', durable=True)
       channel.basic_publish(
           exchange=exchange,
           routing_key=routing_key,
           body=json.dumps(data),
           properties=pika.BasicProperties(delivery_mode=2)  # persistent
       )
       connection.close()
   ```

4. **Emit events when order status changes:**
   ```python
   # store/controllers/orderController/views.py
   from store.events import publish_event
   
   def checkout_view(request):
       # ... create order ...
       publish_event('bookstore.orders', 'order.created', {
           'order_id': order.id,
           'customer_id': order.customer.id,
           'total': order.total_price
       })
   ```

---

## Phase 2: Extract Payment Service (Weeks 2-3)

### Architecture
```
Monolith Calls Payment Service
┌──────────────────────────────┐
│  Django (Monolith)           │
│  - Web UI                    │
│  - Book Catalog              │
│  - Order Management          │
│  - Cart                      │
└──────────┬───────────────────┘
           │ HTTP/REST API Call
           │ (Async via message queue)
           ▼
┌──────────────────────────────┐
│  Payment Service (FastAPI)   │
│  - Stripe Integration        │
│  - Payment Processing        │
│  - Webhook Handling          │
│  - Retry Logic               │
└──────────────────────────────┘
```

### Step 1: Create Payment Service Structure
**Status:** ⬜ Not Started

```bash
# Create directory
mkdir payment-service
cd payment-service

# Create structure
mkdir app routes services tests
touch app.py config.py requirements.txt .env
```

### Step 2: Implement Payment Service
**Status:** ⬜ Not Started

**File: payment-service/app.py**
```python
from fastapi import FastAPI, HTTPException, Header
import stripe
import os
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging

# Configuration
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_...")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///payments.db")

# Database
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class PaymentRecord(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True)
    order_id = Column(String)
    transaction_id = Column(String)
    amount = Column(Float)
    status = Column(String)  # pending, completed, failed

app = FastAPI()
logger = logging.getLogger(__name__)

class PaymentRequest(BaseModel):
    order_id: str
    amount: float
    customer_email: str
    payment_method_id: str

@app.post("/api/v1/payments/process")
async def process_payment(req: PaymentRequest, authorization: str = Header(None)):
    """Process payment using Stripe"""
    
    # Validate auth token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth")
    
    try:
        # Create Stripe charge
        charge = stripe.Charge.create(
            amount=int(req.amount * 100),
            currency="usd",
            source=req.payment_method_id,
            description=f"Order {req.order_id}",
            receipt_email=req.customer_email
        )
        
        # Save to database
        db = SessionLocal()
        payment = PaymentRecord(
            order_id=req.order_id,
            transaction_id=charge.id,
            amount=req.amount,
            status="completed"
        )
        db.add(payment)
        db.commit()
        
        logger.info(f"Payment processed: {charge.id}")
        
        return {
            "status": "success",
            "payment_id": charge.id,
            "order_id": req.order_id,
            "amount": req.amount
        }
        
    except stripe.error.CardError as e:
        logger.error(f"Card error: {e}")
        raise HTTPException(status_code=402, detail="Card declined")
    except Exception as e:
        logger.error(f"Payment error: {e}")
        raise HTTPException(status_code=500, detail="Payment failed")

@app.post("/api/v1/payments/webhook")
async def handle_webhook(event: dict):
    """Handle Stripe webhook events"""
    # Verify signature (implement in production)
    event_type = event.get("type")
    
    if event_type == "charge.succeeded":
        # Publish event for monolith to listen
        publish_event('bookstore.payments', 'payment.completed', {
            'charge_id': event['data']['object']['id'],
            'order_id': event['data']['object']['description']
        })
    
    return {"received": True}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

**File: payment-service/requirements.txt**
```
fastapi==0.104.1
uvicorn==0.24.0
stripe==5.4.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
pika==1.3.2
python-dotenv==1.0.0
```

### Step 3: Update Monolith to Call Payment Service
**Status:** ⬜ Not Started

**File: store/payment_client.py (NEW)**
```python
import requests
import os
from django.conf import settings

PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://localhost:5000")
PAYMENT_SERVICE_TOKEN = os.getenv("PAYMENT_SERVICE_TOKEN")

class PaymentClient:
    @staticmethod
    def process_payment(order_id, amount, customer_email, payment_method_id):
        """Call external Payment Service"""
        try:
            response = requests.post(
                f"{PAYMENT_SERVICE_URL}/api/v1/payments/process",
                json={
                    "order_id": str(order_id),
                    "amount": float(amount),
                    "customer_email": customer_email,
                    "payment_method_id": payment_method_id
                },
                headers={"Authorization": f"Bearer {PAYMENT_SERVICE_TOKEN}"},
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"Payment service error: {str(e)}")
```

**File: store/controllers/orderController/payment_shipping_views.py (MODIFIED)**
```python
from store.payment_client import PaymentClient
from store.models.order.order import Order
from store.models.order.payment import Payment

def process_order_payment(request, order_id):
    """Process payment for order"""
    try:
        order = Order.objects.get(id=order_id)
        
        # Call external Payment Service
        payment_result = PaymentClient.process_payment(
            order_id=order.id,
            amount=order.total_price,
            customer_email=order.customer.user.email,
            payment_method_id=request.POST.get("payment_method_id")
        )
        
        # Create Payment record in monolith
        payment = Payment.objects.create(
            order=order,
            transaction_id=payment_result["payment_id"],
            amount=payment_result["amount"],
            status="completed"
        )
        
        order.payment_status = "paid"
        order.save()
        
        return {"success": True, "payment_id": payment_result["payment_id"]}
        
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### Step 4: Deploy with Docker Compose
**Status:** ⬜ Not Started

**File: docker-compose.yml (ROOT)**
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=False
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/bookstore
      - PAYMENT_SERVICE_URL=http://payment-service:5000
      - PAYMENT_SERVICE_TOKEN=demo-token-123
    depends_on:
      - db
      - payment-service
    command: gunicorn bookstore.wsgi:application --bind 0.0.0.0:8000

  payment-service:
    build: ./payment-service
    ports:
      - "5000:5000"
    environment:
      - STRIPE_SECRET_KEY=sk_test_...
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/payments
    depends_on:
      - db
    command: uvicorn app:app --host 0.0.0.0 --port 5000

  db:
    image: postgres:14
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=bookstore
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      - RABBITMQ_DEFAULT_USER=guest
      - RABBITMQ_DEFAULT_PASS=guest

volumes:
  postgres_data:
```

### Step 5: Test Payment Service
**Status:** ⬜ Not Started

```bash
# 1. Start services
docker-compose up -d

# 2. Check payment service is running
curl http://localhost:5000/health

# 3. Test payment processing
curl -X POST http://localhost:5000/api/v1/payments/process \
  -H "Authorization: Bearer demo-token-123" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "123",
    "amount": 99.99,
    "customer_email": "customer@example.com",
    "payment_method_id": "tok_visa"
  }'

# 4. View logs
docker-compose logs -f payment-service
docker-compose logs -f web
```

---

## Phase 3: Extract Shipping Service (Week 3)

Similar to Payment Service:
- FastAPI app that integrates with carriers (FedEx, UPS, USPS APIs)
- Monolith calls it via REST API
- Publish shipping events (label created, tracking info available)

---

## Phase 4: Extract Inventory Service (Week 4)

**Key feature:** Reservation system to prevent overselling

```python
@app.post("/api/v1/inventory/reserve")
async def reserve_inventory(book_id: str, quantity: int, order_id: str):
    """Reserve inventory when checkout starts"""
    # Check if stock available
    # Create reservation record
    # Return reservation_id
    
@app.post("/api/v1/inventory/confirm")
async def confirm_inventory(reservation_id: str):
    """Confirm when payment succeeds"""
    
@app.post("/api/v1/inventory/release")
async def release_inventory(reservation_id: str):
    """Release if payment fails or order cancelled"""
```

---

## 🔍 Monitoring & Debugging

### Check service health
```bash
curl http://localhost:8000/health
curl http://localhost:5000/health
```

### View database
```bash
# Connect to postgres
psql -h localhost -U postgres -d bookstore
\dt  # List tables
SELECT * FROM store_payment;
```

### View logs
```bash
# Docker logs
docker-compose logs -f web
docker-compose logs -f payment-service

# Individual service
docker-compose logs payment-service --tail=100
```

### Test RabbitMQ
```bash
# RabbitMQ management UI
http://localhost:15672  # user: guest, pass: guest
```

---

## ✅ Checklist: Payment Service Extraction

- [ ] Phase 1 complete (auth, events, data fixes)
- [ ] Payment Service created with FastAPI
- [ ] Monolith updated to call Payment Service
- [ ] Docker Compose configured
- [ ] Services tested locally
- [ ] Stripe webhook integration working
- [ ] Payment retry logic implemented
- [ ] Error handling & logging in place
- [ ] Deployed to staging
- [ ] Load tested (simulate multiple payment requests)
- [ ] Monitoring configured (logs, metrics, alerts)
- [ ] Rollback plan documented

---

## 🚀 Next Steps

1. **Start with Phase 1** - Fix data model and add auth
2. **Deploy locally with Docker Compose** - Verify monolith still works
3. **Extract Payment Service** - First microservice
4. **Test thoroughly** - End-to-end payment flow
5. **Deploy to production** (AWS, GCP, etc.) - Use Kubernetes for scaling

Choose which service to extract first and I'll provide detailed implementation code!
