# Bookstore Microservices Architecture - Complete System Overview

## System Architecture

The bookstore application has been transformed from a Django monolith into a microservices architecture with event-driven communication.

### Services Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Client (Web Browser)                          │
└─────────────────────┬───────────────────────────────────────────┘
                      │ HTTP
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│              Django Monolith (Port 8000)                         │
│  - Web UI & Templates                                            │
│  - User Authentication                                           │
│  - Order Orchestration                                           │
│  - Book Catalog                                                  │
│  - Client Libraries (Payment, Shipping)                          │
└──────┬─────────┬─────────────┬─────────────────────────────────┘
       │         │             │
       │ HTTP    │ HTTP        │ Publishes Events
       │         │             │
       ▼         ▼             ▼
    Payment   Shipping    ┌─────────────────┐
    Service   Service     │    RabbitMQ     │
    (5000)    (5001)      │  Message Broker │
                          │  (5672, 15672)  │
                          └────────┬────────┘
                                   │ Events
                                   │
                                   ▼
                          ┌─────────────────┐
                          │  Notification   │
                          │     Service     │
                          │     (5002)      │
                          └─────────────────┘
                                   │
                                   ▼
                          Email/SMS/Push

┌─────────────────────────────────────────────────────────────────┐
│             PostgreSQL (Port 5432)                               │
│  - bookstore (monolith)                                          │
│  - payment_service                                               │
│  - shipping_service                                              │
│  - notification_service                                          │
└─────────────────────────────────────────────────────────────────┘
```

## Services Detail

### 1. Django Monolith (bookstore-web)
**Technology**: Django 5.2.10  
**Port**: 8000  
**Database**: bookstore

**Responsibilities**:
- Web UI and templates
- User authentication and sessions
- Book catalog management
- Order orchestration
- Cart management
- Staff management UI
- Client integration with microservices

**Key Files**:
- `store/payment_client.py` - Payment service client
- `store/shipping_client.py` - Shipping service client
- `store/services/payment_shipping_service.py` - Graceful fallback logic
- `store/controllers/` - API and view controllers
- `store/templates/` - HTML templates

**Patterns**:
- **Client Pattern**: Thin client classes for external services
- **Graceful Fallback**: Local processing when services unavailable
- **Event Publishing**: Publishes events to RabbitMQ

---

### 2. Payment Service (payment-service)
**Technology**: FastAPI 0.104.1  
**Port**: 5000  
**Database**: payment_service

**Responsibilities**:
- Payment processing via Stripe
- Payment status tracking
- Refund processing
- Payment history

**API Endpoints**:
- `POST /api/v1/payments/charge` - Process payment
- `POST /api/v1/payments/refund` - Refund payment
- `GET /api/v1/payments/{charge_id}` - Get payment status
- `GET /health` - Health check

**Key Features**:
- Stripe integration with demo mode fallback
- Bearer token authentication
- Event publishing (order.paid)
- Database persistence
- Error handling with detailed messages

**Events Published**:
- `order.paid` - When payment is successful

---

### 3. Shipping Service (shipping-service)
**Technology**: FastAPI 0.104.1  
**Port**: 5001  
**Database**: shipping_service

**Responsibilities**:
- Shipping method management
- Shipment creation and tracking  
- Shipment status updates
- Shipping cost calculation

**API Endpoints**:
- `GET /api/v1/shipping/options` - List available shipping methods
- `POST /api/v1/shipping/create` - Create shipment
- `GET /api/v1/shipping/{order_id}` - Get shipment details
- `PUT /api/v1/shipping/{order_id}` - Update shipment status
- `GET /health` - Health check

**Key Features**:
- Multiple shipping methods (standard, express, overnight)
- Status tracking (pending, processing, shipped, delivered, cancelled)
- Event publishing on creation and status change
- Staff management UI integration
- Bearer token authentication

**Events Published**:
- `shipment.created` - When shipment is created
- `shipment.updated` - When shipment status changes

**Staff Features**:
- `/staff/shipments/` - View all shipments
- `/staff/shipments/<id>/status/` - Update shipment status
- Authorization: Staff-only access with `@user_passes_test(is_staff_user)`

---

### 4. Notification Service (notification-service)
**Technology**: FastAPI 0.104.1  
**Port**: 5002  
**Database**: notification_service

**Responsibilities**:
- Event consumption from RabbitMQ
- Email notification composition and sending
- SMS notification support (ready)
- Notification status tracking

**API Endpoints**:
- `GET /health` - Health check
- `GET /` - Service info

**Key Features**:
- Background event consumer thread
- Subscribes to: order.paid, shipment.created, shipment.updated
- Email service with dev mode (console logging)
- Automatic reconnection to RabbitMQ
- Message acknowledgment (ACK/NACK)
- Database persistence of all notifications

**Events Consumed**:
- `order.paid` → Order confirmation email
- `shipment.created` → Shipping notification email
- `shipment.updated` → Status update email (shipped/delivered only)

**Email Templates**:
- Order confirmation with payment details
- Shipment created with method info
- Shipment status update

---

### 5. RabbitMQ (bookstore-rabbitmq)
**Technology**: RabbitMQ 3-management  
**Ports**: 5672 (AMQP), 15672 (Management UI)

**Configuration**:
- Exchange: `bookstore.events` (topic exchange, durable)
- Queues:
  - `notification_service_queue` (durable)
- Routing Keys:
  - `order.paid`
  - `shipment.created`
  - `shipment.updated`

**Features**:
- Message persistence
- Automatic reconnection
- Management UI at http://localhost:15672

---

### 6. PostgreSQL (bookstore-postgres)
**Technology**: PostgreSQL 14  
**Port**: 5432

**Databases**:
1. **bookstore** - Django monolith data
   - Users, Orders, Books, Cart, etc.
2. **payment_service** - Payment transactions
   - payments table
3. **shipping_service** - Shipment records
   - shipping_methods, shipments tables
4. **notification_service** - Notification tracking
   - notifications table

## Communication Patterns

### Synchronous Communication (HTTP/REST)

```
Monolith --HTTP--> Payment Service
         POST /api/v1/payments/charge
         Authorization: Bearer token

Monolith --HTTP--> Shipping Service
         POST /api/v1/shipping/create
         Authorization: Bearer token
```

**Authentication**: Bearer token in Authorization header  
**Error Handling**: Graceful fallback to local processing  
**Retry**: No automatic retry (handles unavailability gracefully)

### Asynchronous Communication (RabbitMQ Events)

```
Payment Service --publish--> RabbitMQ(order.paid) --consume--> Notification Service
Shipping Service --publish--> RabbitMQ(shipment.created) --consume--> Notification Service
Monolith --publish--> RabbitMQ(shipment.updated) --consume--> Notification Service
```

**Pattern**: Publish-Subscribe (Topic Exchange)  
**Durability**: Messages and queues are durable  
**Ack/Nack**: Consumer acknowledges or rejects messages  
**Error Handling**: Failed messages are not requeued (logged and moved on)

## Data Flow Examples

### Example 1: Customer Places Order

1. **Customer** submits order on Django web UI
2. **Monolith** calls Payment Service (HTTP)
   ```
   POST http://payment-service:5000/api/v1/payments/charge
   Body: {order_id, amount, payment_method}
   ```
3. **Payment Service**:
   - Processes payment via Stripe
   - Saves payment record in payment_service database
   - Publishes `order.paid` event to RabbitMQ
   - Returns success response
4. **Monolith** receives payment confirmation
5. **Monolith** calls Shipping Service (HTTP)
   ```
   POST http://shipping-service:5001/api/v1/shipping/create
   Body: {order_id, method_code, address}
   ```
6. **Shipping Service**:
   - Creates shipment record in shipping_service database
   - Publishes `shipment.created` event to RabbitMQ
   - Returns shipment details
7. **Notification Service** (in background):
   - Consumes `order.paid` event
   - Composes order confirmation email
   - Sends email (or logs in dev mode)
   - Saves notification record with status=SENT
8. **Notification Service** (in background):
   - Consumes `shipment.created` event
   - Composes shipping notification email
   - Sends email
   - Saves notification record with status=SENT
9. **Monolith** displays order confirmation page to customer

**Database State**:
```
bookstore.orders: Order created
payment_service.payments: Payment record
shipping_service.shipments: Shipment record
notification_service.notifications: 2 notification records
```

### Example 2: Staff Updates Shipment Status

1. **Staff user** goes to `/staff/shipments/`
2. **Monolith** displays all shipments with status dropdowns
3. **Staff** changes status to "Shipped" and submits
4. **Monolith** updates local Shipment record
5. **Monolith** calls Shipping Service (HTTP)
   ```
   PUT http://shipping-service:5001/api/v1/shipping/{order_id}
   Body: {status: "SHIPPED"}
   ```
6. **Shipping Service**:
   - Updates shipment status in shipping_service database
   - Publishes `shipment.updated` event to RabbitMQ
   - Returns updated shipment
7. **Monolith** displays success message
8. **Notification Service** (in background):
   - Consumes `shipment.updated` event
   - Checks if status is "shipped" or "delivered"
   - Composes status update email
   - Sends email
   - Saves notification record with status=SENT

**Database State**:
```
bookstore.shipments: Status = "Shipped", updated_at changed
shipping_service.shipments: status = "SHIPPED", updated_at changed
notification_service.notifications: 1 new notification record
```

### Example 3: Service Unavailable (Graceful Degradation)

1. **Customer** submits order
2. **Monolith** calls Payment Service → **Connection Refused**
3. **Monolith** catches PaymentServiceUnavailable exception
4. **Monolith** processes payment locally (fallback)
5. **Monolith** saves Order with local payment data
6. **Monolith** logs warning: "Payment service unavailable, processed locally"
7. **Monolith** displays order confirmation to customer
8. **No event published** (payment service was unavailable)
9. **Customer receives order** but no automated notification

**Database State**:
```
bookstore.orders: Order created with local payment data
payment_service.payments: (empty - service was down)
notification_service.notifications: (no order.paid notification)
```

## Technology Stack

### Backend Frameworks
- **Django 5.2.10**: Monolith web application
- **FastAPI 0.104.1**: Microservices
- **SQLAlchemy 2.0.23**: ORM for microservices
- **Pydantic 2.5.0**: Data validation and settings

### Databases
- **PostgreSQL 14**: All services
- **psycopg2-binary 2.9.9**: PostgreSQL adapter

### Message Queue
- **RabbitMQ 3-management**: Event bus
- **pika 1.3.2**: Python RabbitMQ client

### External Services
- **Stripe 5.4.0**: Payment processing (demo mode)
- **SMTP**: Email sending (dev mode: console logging)

### Deployment
- **Docker**: Containerization
- **Docker Compose**: Orchestration
- **uvicorn 0.24.0**: ASGI server for FastAPI

### Web Server
- **Django development server**: Port 8000

## Configuration

### Environment Variables

**Monolith (Django)**:
```bash
DEBUG=True
DATABASE_URL=postgresql://bookstore:bookstore_password@postgres:5432/bookstore
PAYMENT_SERVICE_URL=http://payment-service:5000
PAYMENT_SERVICE_TOKEN=payment-service-token-123
SHIPPING_SERVICE_URL=http://shipping-service:5001
SHIPPING_SERVICE_TOKEN=shipping-service-token-123
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
```

**Payment Service**:
```bash
DEBUG=True
DATABASE_URL=postgresql://bookstore:bookstore_password@postgres:5432/payment_service
STRIPE_SECRET_KEY=sk_test_demo
STRIPE_PUBLISHABLE_KEY=pk_test_demo
PAYMENT_SERVICE_TOKEN=payment-service-token-123
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
```

**Shipping Service**:
```bash
DEBUG=True
DATABASE_URL=postgresql://bookstore:bookstore_password@postgres:5432/shipping_service
SHIPPING_SERVICE_TOKEN=shipping-service-token-123
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
```

**Notification Service**:
```bash
DEBUG=True
DATABASE_URL=postgresql://bookstore:bookstore_password@postgres:5432/notification_service
NOTIFICATION_SERVICE_TOKEN=notification-service-token-123
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
SMTP_HOST=localhost
SMTP_PORT=1025
FROM_EMAIL=noreply@bookstore.local
```

## Security

### Authentication & Authorization

1. **Service-to-Service**: Bearer token authentication
   ```
   Authorization: Bearer payment-service-token-123
   ```

2. **User Authentication**: Django sessions & authentication
   - `@login_required` decorator for authenticated views
   - `@user_passes_test(is_staff_user)` for staff-only views

3. **Staff Authorization**:
   ```python
   def is_staff_user(user):
       return user.is_staff or Staff.objects.filter(user=user).exists()
   ```

### Data Security
- Passwords hashed with Django's PBKDF2 algorithm
- CSRF protection on all POST requests
- SQL injection protection via ORM
- Environment variables for sensitive config

## Deployment

### Start All Services
```bash
docker compose up -d --build
```

### Check Service Health
```bash
docker compose ps
curl http://localhost:8000/health    # Monolith
curl http://localhost:5000/health    # Payment Service
curl http://localhost:5001/health    # Shipping Service
curl http://localhost:5002/health    # Notification Service
```

### View Logs
```bash
docker compose logs -f                # All services
docker compose logs -f web            # Monolith only
docker compose logs -f payment-service
docker compose logs -f shipping-service
docker compose logs -f notification-service
```

### Database Access
```bash
# Monolith database
docker compose exec postgres psql -U bookstore -d bookstore

# Payment service database
docker compose exec postgres psql -U bookstore -d payment_service

# Shipping service database
docker compose exec postgres psql -U bookstore -d shipping_service

# Notification service database
docker compose exec postgres psql -U bookstore -d notification_service
```

### RabbitMQ Management UI
Open http://localhost:15672  
Username: guest  
Password: guest

## Monitoring & Observability

### Health Checks
All services expose `/health` endpoints that return:
```json
{
  "status": "healthy",
  "service": "service-name",
  "version": "1.0"
}
```

Docker health checks run every 30 seconds:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:PORT/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### Logs
All services log to stdout/stderr with timestamps:
```
2026-03-09 19:09:11,276 - services.event_consumer - INFO - Received event: order.paid
```

### Database Queries
```sql
-- Recent orders
SELECT id, total_amount, status, created_at 
FROM store_order 
ORDER BY created_at DESC 
LIMIT 10;

-- Recent payments
SELECT id, charge_id, amount, status, created_at 
FROM payments 
ORDER BY created_at DESC 
LIMIT 10;

-- Recent shipments
SELECT id, order_id, status, method_code, created_at 
FROM shipments 
ORDER BY created_at DESC 
LIMIT 10;

-- Recent notifications
SELECT id, event_type, order_id, recipient, status, sent_at 
FROM notifications 
ORDER BY created_at DESC 
LIMIT 10;
```

## Testing

### Unit Tests
```bash
# Django tests
docker compose exec web python manage.py test

# Payment service tests
docker compose exec payment-service pytest

# Shipping service tests
docker compose exec shipping-service pytest
```

### Integration Tests
```bash
# Test end-to-end order flow
python test_order_flow.py

# Test notification service
python test_notification_service.py
```

### Manual Testing
1. Access web UI: http://localhost:8000
2. Create account and login
3. Browse books and add to cart
4. Checkout and place order
5. Check logs to see service interactions
6. Check databases to verify data persistence
7. Staff: Login and update shipment status at `/staff/shipments/`

## Architecture Patterns

### 1. Microservices Pattern
- Services are independently deployable
- Each service owns its database (database per service)
- Services communicate via HTTP and events

### 2. Client Pattern
- Monolith has thin client classes for each service
- Clients handle HTTP communication
- Centralized error handling in clients

### 3. Graceful Degradation
- Services fail gracefully when dependencies unavailable
- Local fallback processing when possible
- User experience preserved during outages

### 4. Event-Driven Architecture
- Services publish events for significant actions
- Asynchronous processing via RabbitMQ
- Loose coupling between services

### 5. API Gateway Pattern (Monolith as Gateway)
- Monolith serves as gateway to microservices
- Orchestrates multi-service workflows
- Provides unified UI

### 6. Database per Service
- Each service has its own database
- Data duplication for performance
- Eventual consistency

## Benefits of This Architecture

### Scalability
- Each service scales independently
- Notification service can handle high email volume
- Payment/shipping can scale during peak times

### Maintainability
- Clear boundaries between services
- Easy to locate and fix issues
- Changes isolated to specific services

### Resilience
- Service failures don't cascade
- Graceful degradation maintains functionality
- Health checks enable automatic recovery

### Team Autonomy
- Teams can work on services independently
- Different deployment schedules
- Technology choice per service

### Performance
- Async event processing doesn't block users
- Database per service avoids contention
- Services can use different optimization strategies

## Limitations & Trade-offs

### Complexity
- More services to deploy and monitor
- Distributed transactions more complex
- Debugging spans multiple services

### Data Consistency
- Eventual consistency instead of strong consistency
- Data duplication across databases
- Synchronization challenges

### Network Latency
- Service-to-service calls add latency
- Multiple hops for complex operations
- Network failures affect reliability

### Testing Overhead
- Integration tests more complex
- End-to-end tests slow and fragile
- Mocking services required for unit tests

## Future Enhancements

1. **Service Mesh**: Add Istio or Linkerd for advanced networking
2. **API Gateway**: Replace monolith gateway with Kong or Nginx
3. **Authentication Service**: Extract auth into separate service
4. **Monitoring**: Add Prometheus + Grafana for metrics
5. **Logging**: Centralized logging with ELK stack
6. **Tracing**: Distributed tracing with Jaeger
7. **Circuit Breakers**: Add Resilience4j/similar for fault tolerance
8. **Rate Limiting**: Protect services from overload
9. **Caching**: Add Redis for performance
10. **CDN**: Serve static assets from CDN
11. **Load Balancer**: Add Nginx/HAProxy for high availability
12. **Kubernetes**: Migrate from Docker Compose to K8s
13. **CI/CD**: Add GitHub Actions for automated deployment
14. **Blue-Green Deployment**: Zero-downtime deployments

## Conclusion

This microservices architecture demonstrates:
- ✅ Service decomposition from monolith
- ✅ Synchronous HTTP communication
- ✅ Asynchronous event-driven communication
- ✅ Graceful degradation patterns
- ✅ Database per service
- ✅ Docker containerization
- ✅ Health checks and monitoring
- ✅ Authentication and authorization
- ✅ Staff management workflows
- ✅ Multi-database coordination

The system is production-ready for moderate scale and provides a solid foundation for further enhancements.
