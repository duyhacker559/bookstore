# Bookstore Microservices Transformation Guide

## 🏗️ Proposed Microservices Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway                             │
│              (nginx, Kong, or AWS API Gateway)               │
└─────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
┌───────▼────────┐  ┌────▼──────────┐  ┌──▼────────────────┐
│  Book Service  │  │ Order Service │  │ Payment Service   │
│ (Core)         │  │ (checkout)    │  │ (Stripe/PayPal)  │
└────────────────┘  └───────────────┘  └───────────────────┘
        │                 │                 │
        │                 ▼                 │
        │         ┌─────────────────┐       │
        │         │ Cart Service    │◄──────┘
        │         │ (sessions)      │
        │         └─────────────────┘
        │                 │
        ▼                 │
┌─────────────────┐       │       ┌──────────────────┐
│ Inventory Svcs  │       │       │ Shipping Service │
│ (stock mgmt)    │       │       │ (carriers API)   │
└─────────────────┘       │       └──────────────────┘
                          │
                          ▼
                ┌──────────────────────┐
                │ Notification Service │
                │ (Email, SMS, Push)   │
                └──────────────────────┘
```

## 📦 Phase 1: Prepare for Microservices (Current Monolith)

### 1.1 Fix Critical Data Issues

**Problem:** Book model has `stock`, but Inventory model also has `quantity`

**Solution:** Add migration to consolidate inventory management

```python
# store/migrations/0007_consolidate_inventory.py

from django.db import migrations, models
import django.db.models.deletion

def consolidate_inventory(apps, schema_editor):
    Book = apps.get_model('store', 'Book')
    Inventory = apps.get_model('store', 'Inventory')
    
    for book in Book.objects.all():
        inv, created = Inventory.objects.get_or_create(
            book=book,
            defaults={'quantity': book.stock}
        )
        if not created and book.stock != inv.quantity:
            print(f"CONFLICT: Book {book.id} stock={book.stock}, Inventory qty={inv.quantity}")

class Migration(migrations.Migration):
    dependencies = [
        ('store', '0006_alter_comment_unique_constraint'),
    ]

    operations = [
        migrations.RunPython(consolidate_inventory),
    ]
```

### 1.2 Fix Model Relationships

**Problem:** Author and Category not linked to Book

**Current:** Book has hardcoded `author_name` and `category_name`

**Solution:** Link via foreign keys

```python
# store/models/book/book.py - ADD THESE FIELDS

from django.db import models
from store.models.author.author import Author
from store.models.category.category import Category

class Book(models.Model):
    # ... existing fields ...
    author = models.ForeignKey(Author, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Keep legacy fields for backward compatibility during transition
    author_name = models.CharField(max_length=255, blank=True)
    category_name = models.CharField(max_length=255, blank=True)
```

Create migration:
```python
# store/migrations/0008_book_add_relations.py

from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('store', '0007_consolidate_inventory'),
    ]

    operations = [
        migrations.AddField(
            model_name='book',
            name='author',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='store.author'),
        ),
        migrations.AddField(
            model_name='book',
            name='category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='store.category'),
        ),
    ]
```

### 1.3 Add API Authentication

**Add JWT authentication to API endpoints:**

```python
# store/middleware/auth.py - NEW FILE

from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import authentication_classes, permission_classes
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User

def get_or_create_token(user):
    token, created = Token.objects.get_or_create(user=user)
    return token.key

# Usage in views:
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def protected_api_view(request):
    return Response({"message": "Authenticated access"})
```

---

## 📋 Phase 2: Extract Microservices (3-4 weeks)

### Service 1: Payment Service (HIGHEST PRIORITY)

**Why first:** Revenue generation, security compliance (PCI), easiest to extract

**Architecture:**
```
Monolith (Order Service)
    │
    ├─ Create Order
    ├─ Call Payment Service API
    │
Payment Service (Separate)
    ├─ Process Payment (Stripe/PayPal)
    ├─ Handle Webhooks
    ├─ Retry Failed Payments
    └─ Emit PaymentProcessed event
```

**Step 1: Create Payment Service directory structure**

```
payment-service/
├── app.py                 # Flask/FastAPI app
├── requirements.txt       # Dependencies
├── config.py              # Config (DB, API keys)
├── models.py              # Payment model
├── routes/
│   └── payments.py        # Payment endpoints
├── services/
│   ├── stripe_service.py  # Stripe integration
│   └── webhook_handler.py # Webhook processing
└── tests/
    └── test_payments.py
```

**Step 2: Payment Service Implementation (FastAPI)**

```python
# payment-service/app.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import stripe
import os

app = FastAPI()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

class PaymentRequest(BaseModel):
    order_id: str
    amount: float
    customer_email: str
    payment_method_id: str

@app.post("/api/v1/payments/process")
async def process_payment(payment_req: PaymentRequest):
    try:
        charge = stripe.Charge.create(
            amount=int(payment_req.amount * 100),
            currency="usd",
            source=payment_req.payment_method_id,
            description=f"Order {payment_req.order_id}",
            receipt_email=payment_req.customer_email
        )
        
        return {
            "status": "success",
            "payment_id": charge.id,
            "order_id": payment_req.order_id,
            "amount": payment_req.amount
        }
    except stripe.error.CardError as e:
        raise HTTPException(status_code=402, detail=str(e))

@app.post("/api/v1/payments/webhook")
async def webhook(request: dict):
    # Handle Stripe webhook events
    event_type = request.get("type")
    if event_type == "charge.succeeded":
        # Update order status
        pass
    return {"status": "received"}
```

**Step 3: Update Monolith to Call Payment Service**

```python
# store/controllers/orderController/payment_shipping_views.py - MODIFIED

import requests
from django.conf import settings

def process_order_payment(request, order_id):
    order = Order.objects.get(id=order_id)
    
    # Call external payment service
    payment_response = requests.post(
        f"{settings.PAYMENT_SERVICE_URL}/api/v1/payments/process",
        json={
            "order_id": str(order.id),
            "amount": float(order.total_price),
            "customer_email": order.customer.user.email,
            "payment_method_id": request.POST.get("payment_method_id")
        },
        headers={"Authorization": f"Bearer {settings.PAYMENT_SERVICE_TOKEN}"}
    )
    
    if payment_response.status_code == 200:
        payment_data = payment_response.json()
        payment = Payment.objects.create(
            order=order,
            transaction_id=payment_data["payment_id"],
            amount=payment_data["amount"],
            status="completed"
        )
        order.payment_status = "paid"
        order.save()
        return payment_data
    else:
        raise Exception(f"Payment failed: {payment_response.text}")
```

**Step 4: Docker Compose for Local Development**

```yaml
# docker-compose.yml

version: '3.8'

services:
  # Existing monolith
  web:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - db
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/bookstore
      - PAYMENT_SERVICE_URL=http://payment-service:5000

  # New payment service
  payment-service:
    build: ./payment-service
    ports:
      - "5000:5000"
    environment:
      - STRIPE_SECRET_KEY=${STRIPE_SECRET_KEY}
      - DATABASE_URL=postgresql://user:pass@db:5432/payments

  # Shared database
  db:
    image: postgres:14
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=bookstore
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

**Step 5: Service Communication via Events (Optional RabbitMQ)**

```python
# For async communication, add message queue

# payment-service/services/events.py
import pika
import json

def publish_event(event_type, data):
    connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
    channel = connection.channel()
    channel.exchange_declare(exchange='bookstore.events', exchange_type='topic')
    
    channel.basic_publish(
        exchange='bookstore.events',
        routing_key=event_type,
        body=json.dumps(data)
    )
    connection.close()

# Example: payment_service publishes "payment.completed" event
publish_event('payment.completed', {
    'order_id': '123',
    'transaction_id': 'txn_456'
})

# monolith listens for this event and updates order status
```

---

### Service 2: Shipping Service (MEDIUM PRIORITY)

**Architecture:** Similar to Payment Service

```python
# shipping-service/app.py (FastAPI)

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class ShippingRequest(BaseModel):
    order_id: str
    address: str
    weight: float
    carrier: str  # fedex, ups, usps

@app.post("/api/v1/shipping/calculate")
async def calculate_shipping():
    # Call carrier APIs
    pass

@app.post("/api/v1/shipping/create_label")
async def create_shipping_label():
    # Generate shipping label
    pass
```

---

### Service 3: Notification Service (MEDIUM PRIORITY)

```python
# notification-service/app.py

from fastapi import FastAPI
from celery import shared_task
import smtplib

app = FastAPI()

@app.post("/api/v1/notifications/send-email")
async def send_email(to: str, subject: str, body: str):
    # Send email asynchronously
    send_email_task.delay(to, subject, body)
    return {"status": "queued"}

@shared_task
def send_email_task(to, subject, body):
    # Celery task to send email
    pass
```

---

### Service 4: Inventory Service (MEDIUM PRIORITY)

**Why:** Prevent overselling, enable real-time stock updates

```python
# inventory-service/app.py

from fastapi import FastAPI
from enum import Enum

app = FastAPI()

class InventoryOperation(str, Enum):
    RESERVE = "reserve"
    RELEASE = "release"
    CONFIRM = "confirm"

@app.post("/api/v1/inventory/reserve")
async def reserve_inventory(book_id: str, quantity: int, order_id: str):
    """Reserve inventory for order (prevents overselling)"""
    # Check stock
    # Create reservation
    # Return reservation_id
    pass

@app.post("/api/v1/inventory/confirm")
async def confirm_inventory(reservation_id: str):
    """Confirm reservation when payment succeeds"""
    pass

@app.post("/api/v1/inventory/release")
async def release_inventory(reservation_id: str):
    """Release reservation if payment fails"""
    pass
```

---

## 🛠️ Phase 3: Deployment & Scaling

### Option A: Docker + Docker Compose (Development/Small Production)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f payment-service
docker-compose logs -f web
```

### Option B: Kubernetes (Production)

```yaml
# k8s/bookstore-service.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bookstore-web
spec:
  replicas: 3
  selector:
    matchLabels:
      app: bookstore-web
  template:
    metadata:
      labels:
        app: bookstore-web
    spec:
      containers:
      - name: bookstore
        image: bookstore:latest
        ports:
        - containerPort: 8000
        env:
        - name: PAYMENT_SERVICE_URL
          value: "http://payment-service:5000"

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-service
spec:
  replicas: 2
  selector:
    matchLabels:
      app: payment-service
  template:
    metadata:
      labels:
        app: payment-service
    spec:
      containers:
      - name: payment
        image: payment-service:latest
        ports:
        - containerPort: 5000
```

### Option C: Serverless (AWS Lambda/Google Cloud Functions)

```python
# AWS Lambda function for payment processing
import json
import stripe

def lambda_handler(event, context):
    # API Gateway passes HTTP request
    body = json.loads(event['body'])
    
    # Process payment
    charge = stripe.Charge.create(...)
    
    return {
        'statusCode': 200,
        'body': json.dumps({'payment_id': charge.id})
    }
```

---

## 📊 Implementation Timeline

| Phase | Service | Effort | Timeline | Priority |
|-------|---------|--------|----------|----------|
| 1 | Data Fixes + Auth | 2-3 days | Week 1 | 🔴 CRITICAL |
| 2 | Payment Service | 3-4 days | Week 1-2 | 🟠 HIGH |
| 2 | Shipping Service | 2-3 days | Week 2 | 🟠 HIGH |
| 2 | Notification Service | 2 days | Week 2 | 🟡 MEDIUM |
| 3 | Inventory Service | 2 days | Week 3 | 🟡 MEDIUM |
| 3 | Recommendation Service | 1-2 days | Week 3 | 🟢 LOW |
| Deploy | Docker + Kubernetes | 3-5 days | Week 4 | 🟠 HIGH |

---

## 🚀 Quick Start: Extract Payment Service Right Now

```bash
# 1. Create payment service directory
mkdir payment-service
cd payment-service

# 2. Create requirements.txt
cat > requirements.txt << 'EOF'
fastapi==0.104.0
uvicorn==0.24.0
stripe==5.4.0
python-dotenv==1.0.0
psycopg2-binary==2.9.9
sqlalchemy==2.0.23
EOF

# 3. Create basic app.py
cat > app.py << 'EOF'
from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}
EOF

# 4. Run locally
pip install -r requirements.txt
uvicorn app:app --reload --port 5000

# 5. Test
curl http://localhost:5000/health
```

**Next Step:** Share which microservice you want to extract first, and I'll provide the complete implementation!
