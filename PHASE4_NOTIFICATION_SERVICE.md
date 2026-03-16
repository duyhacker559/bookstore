# Phase 4: Notification Service Implementation

## Overview
Phase 4 completes the microservices architecture by implementing a notification service that consumes events from RabbitMQ and sends notifications to customers. This demonstrates a full event-driven architecture with asynchronous pub/sub patterns.

## Architecture

### Notification Service
- **Framework**: FastAPI 0.104.1
- **Port**: 5002
- **Database**: PostgreSQL (notification_service)
- **Event Bus**: RabbitMQ (consumes from bookstore.events exchange)
- **Email**: SMTP (dev mode: console logging)

### Event-Driven Flow
```
Monolith/Services → RabbitMQ → Notification Service → Email/SMS
                   (publish)   (consume)              (send)
```

## Implementation Details

### 1. Core Components

#### Configuration (config.py)
- Environment-driven settings using pydantic-settings
- Database connection (PostgreSQL)
- RabbitMQ connection settings
- SMTP configuration
- Development mode support

#### Database Layer (database.py)
- SQLAlchemy engine and session management
- Auto-initialization on startup
- Notification persistence

#### Data Model (models/notification.py)
```python
class Notification:
    - notification_type: Enum (EMAIL/SMS)
    - recipient: String (email/phone)
    - subject: String (email subject)
    - message: Text (notification content)
    - status: Enum (PENDING/SENT/FAILED)
    - event_type: String (order.paid, shipment.created, etc.)
    - order_id: String (for tracking)
    - error_message: Text (on failure)
    - sent_at: DateTime (timestamp when sent)
```

#### Email Service (services/email_service.py)
- EmailService class with send_email() method
- Dev mode: logs to console instead of sending
- Prod mode: sends via SMTP
- Email composers for each event type:
  - `compose_order_paid_email()` - Order confirmation
  - `compose_shipment_created_email()` - Shipping notification
  - `compose_shipment_updated_email()` - Status update

#### Event Consumer (services/event_consumer.py)
- Background thread that listens to RabbitMQ
- Subscribes to routing keys:
  - `order.paid` - Payment confirmations
  - `shipment.created` - Shipping notifications
  - `shipment.updated` - Status updates (only for shipped/delivered)
- Automatic reconnection on failure
- Event parsing and notification creation
- Error handling with database rollback

#### FastAPI Application (app.py)
- Health endpoint: GET /health
- Root endpoint: GET /
- Startup: Initialize database and start event consumer
- Shutdown: Stop event consumer gracefully

### 2. Event Processing Flow

1. **Event Published**: Monolith or microservice publishes event to RabbitMQ
2. **Event Consumed**: Notification service receives event from queue
3. **Email Composed**: Appropriate email template is generated
4. **Email Sent**: Email service sends (or logs in dev mode)
5. **Notification Recorded**: Database record created with status (PENDING/SENT/FAILED)
6. **ACK/NACK**: Message acknowledged or rejected based on success

### 3. Supported Event Types

#### order.paid
```json
{
  "event_type": "order.paid",
  "data": {
    "order_id": "123",
    "amount": 99.99,
    "customer_email": "customer@example.com"
  }
}
```
Sends order confirmation email with payment details.

#### shipment.created
```json
{
  "event_type": "shipment.created",
  "data": {
    "order_id": "123",
    "method_name": "Express Shipping",
    "method_code": "express"
  }
}
```
Sends shipment notification when order is prepared for shipping.

#### shipment.updated
```json
{
  "event_type": "shipment.updated",
  "data": {
    "order_id": "123",
    "previous_status": "processing",
    "current_status": "shipped"
  }
}
```
Sends status update email (only for "shipped" or "delivered" states).

## Docker Configuration

### Dockerfile
- Base image: Python 3.11-slim
- Installs PostgreSQL client and curl
- Health check on /health endpoint
- Runs uvicorn on port 5002

### docker-compose.yml
Added notification-service:
```yaml
notification-service:
  build: ./notification-service
  ports: ["5002:5002"]
  environment:
    - DATABASE_URL=postgresql://bookstore:bookstore_password@postgres:5432/notification_service
    - RABBITMQ_HOST=rabbitmq
    - SMTP_HOST=localhost
    - SMTP_PORT=1025
    - FROM_EMAIL=noreply@bookstore.local
  depends_on:
    - postgres (healthy)
    - rabbitmq (healthy)
```

## Database Schema

### notifications table
```sql
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    notification_type notificationtype NOT NULL,  -- EMAIL or SMS
    recipient VARCHAR(255) NOT NULL,
    subject VARCHAR(500),
    message TEXT NOT NULL,
    status notificationstatus NOT NULL,  -- PENDING, SENT, FAILED
    event_type VARCHAR(100),
    order_id VARCHAR(255),
    error_message TEXT,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    sent_at TIMESTAMP
);

CREATE INDEX ix_notifications_id ON notifications (id);
CREATE INDEX ix_notifications_order_id ON notifications (order_id);
CREATE INDEX ix_notifications_event_type ON notifications (event_type);
CREATE INDEX ix_notifications_recipient ON notifications (recipient);
```

## Testing

### Test Script (test_notification_service.py)
Created a test script that publishes events to RabbitMQ to verify the notification service.

### End-to-End Validation

1. **Published 3 test events**:
   - order.paid for TEST-001
   - shipment.created for TEST-002
   - shipment.updated for TEST-003

2. **Verified event consumption**:
   ```
   Received event: order.paid
   Order paid notification: sent
   
   Received event: shipment.created
   Shipment created notification: sent
   
   Received event: shipment.updated
   Shipment updated notification: sent
   ```

3. **Verified database persistence**:
   ```
   id | event_type       | order_id | recipient            | status
   ---+------------------+----------+----------------------+-------
    1 | order.paid       | TEST-001 | test@example.com     | SENT
    2 | shipment.created | TEST-002 | customer@example.com | SENT
    3 | shipment.updated | TEST-003 | customer@example.com | SENT
   ```

4. **Verified email composition**:
   All emails were logged in dev mode with proper subjects and bodies.

## Service Health

### Container Status
```
bookstore-notification-service   Up (healthy)   0.0.0.0:5002->5002/tcp
```

### Health Endpoint
```bash
curl http://localhost:5002/health
# Response: {"status": "healthy", "service": "notification-service", "version": "1.0"}
```

## Key Features

### ✅ Event-Driven Architecture
- Fully decoupled from monolith and other services
- Asynchronous event consumption
- No synchronous dependencies

### ✅ Reliable Processing
- Message acknowledgment (ACK/NACK)
- Database transactions with rollback on failure
- Error logging with error_message field

### ✅ Flexible Notification Channels
- Email support (SMTP)
- SMS support ready (models support it)
- Extensible to push notifications, webhooks, etc.

### ✅ Development Mode
- Console logging instead of actual email sending
- Easy testing without SMTP server
- Production-ready with simple config change

### ✅ Monitoring & Tracking
- All notifications stored in database
- Status tracking (PENDING/SENT/FAILED)
- Event type and order ID for correlation
- Timestamp tracking (created_at, updated_at, sent_at)

### ✅ Graceful Degradation
- Consumer continues on individual event failures
- Automatic reconnection to RabbitMQ
- Health checks for monitoring

## Integration with Existing Services

### Payment Service
When payment is successful, publishes `order.paid` event → Notification service sends order confirmation email.

### Shipping Service
- When shipment is created, publishes `shipment.created` event → Notification service sends shipping notification.
- When shipment status changes, publishes `shipment.updated` event → Notification service sends status update email (for shipped/delivered only).

### Monolith (Django)
Continues to publish events to RabbitMQ as before. Notification service is a passive consumer with no impact on existing flows.

## Files Created

1. `notification-service/config.py` - Configuration management
2. `notification-service/database.py` - Database setup
3. `notification-service/models/notification.py` - Data model
4. `notification-service/models/__init__.py` - Package exports
5. `notification-service/services/email_service.py` - Email sending logic
6. `notification-service/services/event_consumer.py` - RabbitMQ consumer
7. `notification-service/services/__init__.py` - Package init
8. `notification-service/app.py` - FastAPI application
9. `notification-service/requirements.txt` - Python dependencies
10. `notification-service/Dockerfile` - Container definition
11. `notification-service/.env.example` - Environment template
12. `test_notification_service.py` - Test script for validation

### docker-compose.yml Updated
Added notification-service configuration with health checks and dependencies.

## Multi-Database Architecture

The system now operates with **4 PostgreSQL databases**:
1. **bookstore** - Django monolith data
2. **payment_service** - Payment transactions
3. **shipping_service** - Shipment records
4. **notification_service** - Notification tracking

## Architecture Benefits

### Separation of Concerns
- Notification logic isolated from business logic
- Each service has single responsibility
- Easy to modify notification templates without touching core services

### Scalability
- Notification service can scale independently
- Multiple consumers can process events in parallel
- No blocking on email sending in critical paths

### Reliability
- Event persistence in RabbitMQ (durable queues)
- Notification status tracking in database
- Failed notifications can be retried

### Auditability
- Complete notification history in database
- Track when notifications were sent
- Investigate customer "didn't receive email" issues

### Maintainability
- Clear separation of email templates
- Easy to add new notification types
- Centralized notification logic

## Monitoring & Operations

### Check Service Health
```bash
docker compose ps notification-service
curl http://localhost:5002/health
```

### View Logs
```bash
docker compose logs notification-service --tail=50 --follow
```

### Query Notifications
```bash
docker compose exec postgres psql -U bookstore -d notification_service \
  -c "SELECT id, event_type, order_id, recipient, status, sent_at FROM notifications ORDER BY id DESC LIMIT 10;"
```

### Republish Failed Notifications
Future enhancement: Add admin endpoint to retry failed notifications.

## Future Enhancements

1. **SMS Support**: Implement SMS sending via Twilio/AWS SNS
2. **Push Notifications**: Add mobile push notification support
3. **Retry Logic**: Implement exponential backoff for failed sends
4. **Admin UI**: Create notification management dashboard
5. **Templates**: Move to database-driven email templates
6. **Personalization**: Fetch customer preferences for notification channels
7. **Analytics**: Track open rates, click rates, etc.
8. **Webhooks**: Support webhook notifications for integrations
9. **Batching**: Group notifications for efficiency
10. **Priority Queue**: Separate queues for urgent vs. standard notifications

## Conclusion

Phase 4 successfully implements a notification service that:
- ✅ Consumes events from RabbitMQ asynchronously
- ✅ Composes and sends notifications (email)
- ✅ Persists notification records with status tracking
- ✅ Operates independently from other services
- ✅ Completes the event-driven architecture demonstration

The bookstore system now has a complete microservices architecture with:
- **Payment Service**: Payment processing
- **Shipping Service**: Shipping management with staff UI
- **Notification Service**: Customer communications
- **Monolith**: Django web application coordinating everything
- **Event Bus**: RabbitMQ enabling async communication

All services are containerized, health-checked, and operating in a coordinated multi-database environment.
