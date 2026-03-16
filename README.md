# Bookstore Microservices Platform

A full-featured e-commerce bookstore demonstrating microservices architecture with Django monolith, FastAPI services, event-driven communication via RabbitMQ, and multi-database persistence.

## 🏗️ Architecture Overview

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │ HTTP
       ▼
┌─────────────────────────────────────────────────┐
│         Django Monolith (Port 8000)             │
│  • Web UI & Authentication                      │
│  • Order Orchestration                          │
│  • Book Catalog Management                      │
└─────┬─────────────┬──────────────┬──────────────┘
      │ REST        │ REST         │ Events
      ▼             ▼              ▼
┌──────────┐  ┌───────────┐  ┌──────────────┐
│ Payment  │  │ Shipping  │  │  RabbitMQ    │
│ Service  │  │ Service   │  │ (Port 5672)  │
│ (5000)   │  │ (5001)    │  └──────┬───────┘
└────┬─────┘  └─────┬─────┘         │ Consume
     │              │               ▼
     │              │         ┌──────────────┐
     │              │         │Notification  │
     │              │         │  Service     │
     │              │         │  (5002)      │
     │              │         └──────────────┘
     ▼              ▼
┌─────────────────────────────────────────────────┐
│    PostgreSQL (Port 5432) - 4 Databases         │
│  • bookstore         • shipping_service         │
│  • payment_service   • notification_service     │
└─────────────────────────────────────────────────┘
```

## 📦 Services

### Django Monolith (Port 8000)
- **Purpose:** Web application, user authentication, order orchestration, book catalog
- **Technology:** Django 5.2.10, PostgreSQL
- **Database:** `bookstore`
- **Key Features:**
  - Customer & staff authentication
  - Book browsing and search
  - Shopping cart
  - Order management
  - Staff shipment management UI

### Payment Service (Port 5000)
- **Purpose:** Payment processing via Stripe
- **Technology:** FastAPI 0.104.1, SQLAlchemy, Stripe SDK
- **Database:** `payment_service`
- **Key Features:**
  - Payment processing (demo mode: `sk_test_demo`)
  - Refund processing
  - Payment history
  - Publishes `order.paid` events

### Shipping Service (Port 5001)
- **Purpose:** Shipping management and tracking
- **Technology:** FastAPI 0.104.1, SQLAlchemy
- **Database:** `shipping_service`
- **Key Features:**
  - Multiple shipping methods (standard, express, overnight)
  - Shipment creation and tracking
  - Status updates (pending, processing, shipped, delivered, cancelled)
  - Publishes `shipment.created` and `shipment.updated` events

### Notification Service (Port 5002)
- **Purpose:** Event-driven customer notifications
- **Technology:** FastAPI 0.104.1, SQLAlchemy, RabbitMQ consumer
- **Database:** `notification_service`
- **Key Features:**
  - Consumes `order.paid`, `shipment.created`, `shipment.updated` events
  - Email composition and sending (dev mode: console logging)
  - SMS support (ready, not enabled)
  - Notification history and status tracking

### Infrastructure
- **PostgreSQL 14:** 4 databases (database-per-service pattern)
- **RabbitMQ 3:** Event bus with topic exchange (`bookstore.events`)
- **Docker Compose:** Orchestration with health checks

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Git
- 4GB+ RAM available

### 1. Clone & Start

```bash
# Clone the repository
git clone <repository-url>
cd bookstore

# Start all services
docker compose up -d --build

# Wait 30-60 seconds for all services to become healthy
docker compose ps
```

### 2. Verify Health

```bash
# Check all services are healthy
docker compose ps

# Test health endpoints
curl http://localhost:8000/health  # Monolith
curl http://localhost:5000/health  # Payment Service
curl http://localhost:5001/health  # Shipping Service
curl http://localhost:5002/health  # Notification Service
```

### 3. Access the Application

- **Web Application:** http://localhost:8000
- **RabbitMQ Management:** http://localhost:15672 (guest/guest)
- **PostgreSQL:** localhost:5432 (bookstore/bookstore_password)

### 4. Create Test Data (Optional)

```bash
# Populate books
docker compose exec web python manage.py populate_books

# Create superuser
docker compose exec web python manage.py createsuperuser
```

### 5. Run End-to-End Test

```bash
# Test complete order flow across all services
docker compose exec web python test_e2e_order.py
```

## 📚 Common Commands

### Service Management

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose stop

# Restart a specific service
docker compose restart payment-service

# View logs
docker compose logs -f                    # All services
docker compose logs -f payment-service    # Specific service
docker compose logs --tail=50 web         # Last 50 lines

# Check service status
docker compose ps
```

### Database Operations

```bash
# Access PostgreSQL
docker compose exec postgres psql -U bookstore -d bookstore

# List all databases
docker compose exec postgres psql -U bookstore -c "\l"

# Query specific database
docker compose exec postgres psql -U bookstore -d payment_service -c "SELECT * FROM payments LIMIT 5;"

# Check notifications
docker compose exec postgres psql -U bookstore -d notification_service -c "SELECT id, event_type, order_id, status FROM notifications ORDER BY id DESC LIMIT 10;"
```

### Django Management

```bash
# Run migrations
docker compose exec web python manage.py migrate

# Create superuser
docker compose exec web python manage.py createsuperuser

# Django shell
docker compose exec web python manage.py shell

# Collect static files
docker compose exec web python manage.py collectstatic
```

### Testing

```bash
# End-to-end order test
docker compose exec web python test_e2e_order.py

# Notification service test
python test_notification_service.py

# Django tests
docker compose exec web python manage.py test
```

### RabbitMQ

```bash
# List exchanges
docker compose exec rabbitmq rabbitmqctl list_exchanges

# List queues
docker compose exec rabbitmq rabbitmqctl list_queues

# List bindings
docker compose exec rabbitmq rabbitmqctl list_bindings
```

### Clean Restart

```bash
# Stop everything and remove volumes (fresh start)
docker compose down -v

# Rebuild and start
docker compose up -d --build

# Databases will be automatically initialized via init-db.sh
```

## 🔧 Configuration

### Environment Variables

Each service can be configured via environment variables in `docker-compose.yml`:

**Monolith:**
- `DEBUG` - Django debug mode
- `DATABASE_URL` - PostgreSQL connection string
- `PAYMENT_SERVICE_URL` - Payment service endpoint
- `PAYMENT_SERVICE_TOKEN` - Bearer token for payment service
- `SHIPPING_SERVICE_URL` - Shipping service endpoint
- `SHIPPING_SERVICE_TOKEN` - Bearer token for shipping service
- `RABBITMQ_HOST/PORT/USER/PASSWORD` - RabbitMQ connection

**Payment Service:**
- `DATABASE_URL` - PostgreSQL connection (payment_service)
- `STRIPE_SECRET_KEY` - Stripe API key (default: `sk_test_demo`)
- `PAYMENT_SERVICE_TOKEN` - API authentication token
- `RABBITMQ_HOST/PORT/USER/PASSWORD` - RabbitMQ connection

**Shipping Service:**
- `DATABASE_URL` - PostgreSQL connection (shipping_service)
- `SHIPPING_SERVICE_TOKEN` - API authentication token
- `RABBITMQ_HOST/PORT/USER/PASSWORD` - RabbitMQ connection

**Notification Service:**
- `DATABASE_URL` - PostgreSQL connection (notification_service)
- `RABBITMQ_HOST/PORT/USER/PASSWORD` - RabbitMQ connection
- `SMTP_HOST/PORT/FROM_EMAIL` - Email configuration (dev mode uses console)

## 🏛️ Architecture Patterns

### Database Per Service
Each microservice owns its database, ensuring loose coupling and independent scalability.

### Client Pattern
Monolith uses thin client libraries (`PaymentClient`, `ShippingClient`) to communicate with services via REST APIs.

### Event-Driven Architecture
Services publish events to RabbitMQ topic exchange. Notification service consumes events asynchronously for customer communication.

### Graceful Degradation
Services handle dependency failures gracefully:
- If payment service is down → process locally and warn
- If shipping service is down → create local shipment record
- User experience maintained during partial outages

### Bearer Token Authentication
Service-to-service calls authenticated via Bearer tokens in Authorization headers.

## 📖 API Documentation

### Payment Service API

```bash
# Process payment
POST /api/v1/payments/process
Headers: Authorization: Bearer payment-service-token-123
Body: {
  "order_id": "123",
  "amount": 99.99,
  "currency": "USD",
  "customer_email": "customer@example.com",
  "payment_method_id": "pm_card_visa"
}

# Get payment status
GET /api/v1/payments/{charge_id}
Headers: Authorization: Bearer payment-service-token-123

# Refund payment
POST /api/v1/payments/refund
Headers: Authorization: Bearer payment-service-token-123
Body: {
  "charge_id": "ch_...",
  "amount": 99.99,
  "reason": "Customer request"
}
```

### Shipping Service API

```bash
# Get shipping options
GET /api/v1/shipping/options
Headers: Authorization: Bearer shipping-service-token-123

# Create shipment
POST /api/v1/shipping/create
Headers: Authorization: Bearer shipping-service-token-123
Body: {
  "order_id": "123",
  "method_code": "standard",
  "address": "123 Main St, City, ST 12345",
  "fee": 15.00
}

# Get shipment status
GET /api/v1/shipping/{order_id}
Headers: Authorization: Bearer shipping-service-token-123

# Update shipment status (staff only)
PUT /api/v1/shipping/{order_id}
Headers: Authorization: Bearer shipping-service-token-123
Body: {
  "status": "shipped"
}
```

## 🎯 Use Cases

### Customer Journey
1. Browse books at http://localhost:8000
2. Add books to cart
3. Checkout → Payment processing via payment-service
4. Order confirmation → shipment created via shipping-service
5. Email notifications sent via notification-service
6. Track shipment status

### Staff Workflow
1. Login as staff user
2. Navigate to `/staff/shipments/`
3. View all shipments with current status
4. Update shipment status (processing → shipped → delivered)
5. Status synced to shipping-service database
6. Customer notified via email automatically

## 📊 Monitoring

### Health Checks
All services expose `/health` endpoints:
- Returns 200 OK when healthy
- Docker health checks run every 30 seconds
- View status: `docker compose ps`

### Logs
```bash
# Real-time logs
docker compose logs -f

# Service-specific logs
docker compose logs -f payment-service

# Filter logs
docker compose logs notification-service | grep "order.paid"
```

### RabbitMQ Management UI
- URL: http://localhost:15672
- Username: `guest`
- Password: `guest`
- View: Queues, exchanges, bindings, message rates

### Database Monitoring
```bash
# Connection count
docker compose exec postgres psql -U bookstore -c "SELECT count(*) FROM pg_stat_activity;"

# Database sizes
docker compose exec postgres psql -U bookstore -c "SELECT pg_database.datname, pg_size_pretty(pg_database_size(pg_database.datname)) FROM pg_database;"

# Table sizes
docker compose exec postgres psql -U bookstore -d bookstore -c "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) FROM pg_tables ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC LIMIT 10;"
```

## 🐛 Troubleshooting

### Services Won't Start
```bash
# Check logs
docker compose logs

# Verify ports aren't in use
netstat -an | findstr "8000 5000 5001 5002 5432 5672"

# Clean restart
docker compose down -v
docker compose up -d --build
```

### Database Connection Errors
```bash
# Verify postgres is healthy
docker compose ps postgres

# Check database existence
docker compose exec postgres psql -U bookstore -c "\l"

# Databases should auto-create via init-db.sh
# If not, create manually:
docker compose exec postgres psql -U bookstore -d postgres -c "CREATE DATABASE payment_service;"
docker compose exec postgres psql -U bookstore -d postgres -c "CREATE DATABASE shipping_service;"
docker compose exec postgres psql -U bookstore -d postgres -c "CREATE DATABASE notification_service;"
```

### Service Authentication Failures
```bash
# Verify tokens match in docker-compose.yml
# Monolith's PAYMENT_SERVICE_TOKEN must match payment-service's PAYMENT_SERVICE_TOKEN
# Same for SHIPPING_SERVICE_TOKEN
```

### Events Not Being Consumed
```bash
# Check RabbitMQ
docker compose logs rabbitmq

# Check notification service logs
docker compose logs notification-service

# Verify queue bindings
docker compose exec rabbitmq rabbitmqctl list_bindings

# Test event publishing
python test_notification_service.py
```

## 📁 Project Structure

```
bookstore/
├── docker-compose.yml          # Service orchestration
├── init-db.sh                  # Database initialization script
├── Dockerfile                  # Monolith container
├── manage.py                   # Django management
├── bookstore/                  # Django project settings
├── store/                      # Django app (monolith)
│   ├── models/                 # Data models
│   ├── controllers/            # Views and API controllers
│   ├── templates/              # HTML templates
│   ├── payment_client.py       # Payment service client
│   ├── shipping_client.py      # Shipping service client
│   └── events.py               # RabbitMQ event publishing
├── payment-service/            # Payment microservice
│   ├── app.py                  # FastAPI application
│   ├── routes/                 # API endpoints
│   ├── services/               # Business logic
│   ├── models/                 # Database models
│   ├── Dockerfile
│   └── requirements.txt
├── shipping-service/           # Shipping microservice
│   ├── app.py
│   ├── routes/
│   ├── services/
│   ├── models/
│   ├── Dockerfile
│   └── requirements.txt
├── notification-service/       # Notification microservice
│   ├── app.py
│   ├── services/
│   │   ├── event_consumer.py   # RabbitMQ consumer
│   │   └── email_service.py    # Email sending
│   ├── models/
│   ├── Dockerfile
│   └── requirements.txt
├── test_e2e_order.py           # End-to-end test script
└── test_notification_service.py # Notification test script
```

## 📝 Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Detailed architecture overview
- **[PHASE4_NOTIFICATION_SERVICE.md](PHASE4_NOTIFICATION_SERVICE.md)** - Notification service implementation
- **[RELEASE_READINESS_REPORT.md](RELEASE_READINESS_REPORT.md)** - Production readiness assessment

## 🔐 Security Considerations

### Current Implementation (Demo/Staging)
- Bearer tokens in environment variables
- Stripe demo mode (no real charges)
- SMTP console logging (no real emails)
- No rate limiting
- Basic authentication only

### Production Requirements
- [ ] Move secrets to AWS Secrets Manager / HashiCorp Vault
- [ ] Set up real Stripe account with webhook verification
- [ ] Configure production SMTP server with TLS
- [ ] Implement rate limiting
- [ ] Add request/response encryption
- [ ] Set up API gateway with OAuth2
- [ ] Enable HTTPS only
- [ ] Add WAF (Web Application Firewall)
- [ ] Implement audit logging

## 🚀 Production Deployment

See [RELEASE_READINESS_REPORT.md](RELEASE_READINESS_REPORT.md) for:
- Production readiness checklist
- Known limitations
- Deployment recommendations
- Performance characteristics
- Next steps for hardening

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is for educational and demonstration purposes.

## 💡 Key Learnings

This project demonstrates:
- ✅ Microservices decomposition
- ✅ Database per service pattern
- ✅ Event-driven architecture (pub/sub)
- ✅ Synchronous REST communication
- ✅ Asynchronous message processing
- ✅ Service client pattern
- ✅ Graceful degradation
- ✅ Bearer token authentication
- ✅ Docker containerization
- ✅ Health monitoring
- ✅ Multi-database persistence

## 🆘 Support

For issues and questions:
1. Check [Troubleshooting](#-troubleshooting) section
2. Review service logs: `docker compose logs -f`
3. Verify configuration in `docker-compose.yml`
4. Check [RELEASE_READINESS_REPORT.md](RELEASE_READINESS_REPORT.md)

---

**Built with:** Django • FastAPI • PostgreSQL • RabbitMQ • Docker • Stripe • SQLAlchemy • Pydantic
