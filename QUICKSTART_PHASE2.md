# 🚀 Phase 2 Quick Start Guide

**Phase Complete:** Payment Service Extraction  
**Ready to Deploy:** Yes ✅

---

## 📋 Checklist Before Running

- [ ] Docker and Docker Compose installed
- [ ] Environment files configured (`.env` files created)
- [ ] Stripe keys added (if testing real payments)
- [ ] Port 8000, 5000, 5432, 5672 available

---

## 🏃 Quick Start (5 minutes)

### 1️⃣ Prepare Environment Files

```bash
# Navigate to workspace
cd l:/bookstore

# Create payment service env file if needed
cd payment-service
cp .env.example .env
cd ..
```

Update payment-service/.env with Stripe keys (optional for testing).

### 2️⃣ Start All Services

```bash
# Build images and start services
docker-compose up -d

# Verify all services are healthy
docker-compose ps

# Expected output:
# NAME              STATUS
# postgres          Up (healthy)
# rabbitmq          Up (healthy)
# payment-service   Up (healthy)
# web               Up (healthy)
```

Check services took 30-60 seconds to fully initialize.

### 3️⃣ Initialize Databases

```bash
# Run Django migrations for monolith
docker-compose exec web python manage.py migrate

# Check output - should see "No migrations to apply"
# or list of applied migrations
```

### 4️⃣ Create API Tokens

```bash
# Get a token for yourself
docker-compose exec web python manage.py create_api_token -u admin

# Token output (save this):
# Token: {token_value}
# User: admin
```

### 5️⃣ Create Service Token for Payment Service

```bash
# Create token for payment service to authenticate with monolith
docker-compose exec web python manage.py create_api_token --service payment-service

# Token output (for payment-service)
```

### 6️⃣ Verify All Services Are Responding

```bash
# Test monolith
curl http://localhost:8000

# Test payment service
curl http://localhost:5000/health

# Expected response:
# {"status":"healthy","service":"payment-service","version":"1.0.0"}

# Test RabbitMQ management UI
# Visit: http://localhost:15672
# Login: guest / guest
```

---

## 🧪 Test Payment Processing

### Create a Test Order

```bash
# First, get token from create_api_token command above
export TOKEN="{token_from_step_4}"

# Create a test order
curl -X POST http://localhost:8000/api/orders/ \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"book_id": 1, "quantity": 1}
    ],
    "shipping_address": "123 Main St",
    "billing_address": "123 Main St"
  }'

# Save the order_id from response
export ORDER_ID="order_id_from_response"
```

### Process Payment via Payment Service

```bash
# Get payment service token (from step 5)
export PS_TOKEN="{payment_service_token}"

# Process the payment
curl -X POST http://localhost:5000/api/v1/payments/process \
  -H "Authorization: Bearer ${PS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "'${ORDER_ID}'",
    "amount": 29.99,
    "currency": "USD",
    "customer_email": "customer@example.com",
    "payment_method_id": "tok_visa"
  }'

# Response (success):
# {
#   "status": "succeeded",
#   "payment_id": "ch_...",
#   "order_id": "order_...",
#   "message": "Payment processed successfully"
# }

# Response (failure - declined card):
# {
#   "status": "failed",
#   "error": "Card Declined",
#   "order_id": "order_..."
# }
```

### Check Payment Status

```bash
curl http://localhost:5000/api/v1/payments/${ORDER_ID} \
  -H "Authorization: Bearer ${PS_TOKEN}"

# Response:
# {
#   "order_id": "order_...",
#   "status": "completed",
#   "amount": 29.99,
#   "transaction_id": "ch_...",
#   "created_at": "2026-03-09T12:00:00",
#   "updated_at": "2026-03-09T12:05:00"
# }
```

---

## 🔍 Monitor Services

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web
docker-compose logs -f payment-service
docker-compose logs -f postgres
docker-compose logs -f rabbitmq

# Last 100 lines
docker-compose logs --tail=100 web

# Tail a service and filter
docker-compose logs -f payment-service | grep ERROR
```

### Database Access

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U bookstore -d payment_service

# In PostgreSQL:
\dt                    # List tables
SELECT * FROM payments; # View payments
\q                     # Exit
```

### RabbitMQ Management

```
# Visit: http://localhost:15672
# Login: guest / guest
# View: 
#   - Connections
#   - Channels
#   - Queues
#   - Exchanges
#   - Messages published
```

---

## 🛑 Stop Services

```bash
# Stop and remove containers (keep volumes)
docker-compose down

# Stop including volumes (clean slate)
docker-compose down -v

# Just pause (restart with docker-compose up -d)
docker-compose stop
docker-compose start
```

---

## 🆘 Troubleshooting

### Services not starting?

```bash
# Check Docker Compose version
docker-compose --version  # Should be 1.29+

# Build services fresh
docker-compose build

# Start with verbose output
docker-compose -f docker-compose.yml up --verbose

# Check specific service
docker-compose logs payment-service
```

### Port already in use?

```bash
# Find what's using port 5000
netstat -ano | findstr :5000  # Windows
lsof -i :5000                 # Mac/Linux

# Alternative: Change ports in docker-compose.yml
# payment-service:
#   ports:
#     - "5001:5000"  # Changed from 5000:5000 to 5001:5000
```

### Database not initialized?

```bash
# Check if migrations ran
docker-compose exec web python manage.py showmigrations

# Run migrations manually
docker-compose exec web python manage.py migrate

# Clear and reinitialize
docker-compose exec postgres psql -U bookstore -d payment_service -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
```

### Payment Service not responding?

```bash
# Check service logs
docker-compose logs payment-service

# Check if port is open
curl -v http://localhost:5000/health

# Rebuild and restart
docker-compose up -d --build payment-service
```

---

## 📊 Expected Status

After successful startup:

```
Service            Port   Status    Check Command
─────────────────────────────────────────────────────
PostgreSQL         5432   Healthy   docker-compose ps
RabbitMQ           5672   Healthy   docker-compose ps
Payment Service    5000   Healthy   curl http://localhost:5000/health
Web (Monolith)     8000   Healthy   curl http://localhost:8000
```

---

## 📈 Next: Load Testing

Once all services are healthy, test under load:

```bash
# Install locust (load testing tool)
pip install locust

# Create locustfile.py
# See full Phase 2 implementation guide for details

# Run load test
locust -f locustfile.py --host=http://localhost:5000 --users 100 --spawn-rate 10
```

---

## 🎓 Architecture Overview

```
┌─────────────────────────────────────────────┐
│  Client Request (Checkout)                   │
└──────────────────┬──────────────────────────┘
                   │
        ┌──────────▼──────────┐
        │  Monolith (Django)  │
        │  Port 8000          │
        └──────────┬──────────┘
                   │ (Calls external service)
        ┌──────────▼─────────────────┐
        │  Payment Service (FastAPI)  │
        │  Port 5000                  │
        ├─────────────────────────────┤
        │  - Stripe Integration       │
        │  - Payment Processing       │
        │  - Refund Management        │
        └──────────┬─────────────────┘
                   │
    ┌──────────────┼──────────────┐
    │              │              │
┌───▼──┐    ┌─────▼────┐    ┌───▼──┐
│Stripe│    │PostgreSQL│    │Rabbit│
│      │    │Database  │    │MQ    │
└──────┘    │Port 5432 │    │5672  │
            └──────────┘    └──────┘
```

---

## 💡 Tips & Tricks

### Restart a single service without stopping others
```bash
docker-compose restart payment-service
```

### View resource usage
```bash
docker stats
```

### Execute commands in a running container
```bash
docker-compose exec payment-service bash
# Now you're in the container bash shell
```

### Clean up Docker
```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune

# Full cleanup (BE CAREFUL!)
docker system prune -a
```

---

## ✅ Phase 2 Status

- ✅ Payment Service implemented
- ✅ Docker Compose setup
- ✅ Environment configured
- ✅ Ready for deployment

**Next:** Run `docker-compose up -d` and test!

---

**Questions?** Check full Phase 2 Implementation Guide or server logs with `docker-compose logs -f`
