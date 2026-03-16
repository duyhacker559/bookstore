#!/usr/bin/env python3
"""
Generate Technical Report PDF for Bookstore Microservices System
Similar structure to the architecture analysis document from the student assignment
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image
from reportlab.lib import colors
from datetime import datetime
from pathlib import Path

# Document setup
pdf_path = r'l:\bookstore\TECHNICAL_REPORT_BOOKSTORE_MICROSERVICES.pdf'
doc = SimpleDocTemplate(pdf_path, pagesize=letter,
                        rightMargin=0.75*inch, leftMargin=0.75*inch,
                        topMargin=0.75*inch, bottomMargin=0.75*inch)

# Get default styles and create custom ones
styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    'CustomTitle',
    parent=styles['Heading1'],
    fontSize=24,
    textColor=colors.HexColor('#1f4788'),
    spaceAfter=30,
    alignment=TA_CENTER,
    fontName='Helvetica-Bold'
)

heading1_style = ParagraphStyle(
    'CustomHeading1',
    parent=styles['Heading1'],
    fontSize=16,
    textColor=colors.HexColor('#2c5aa0'),
    spaceAfter=12,
    spaceBefore=12,
    fontName='Helvetica-Bold'
)

heading2_style = ParagraphStyle(
    'CustomHeading2',
    parent=styles['Heading2'],
    fontSize=13,
    textColor=colors.HexColor('#3a6bb0'),
    spaceAfter=10,
    spaceBefore=10,
    fontName='Helvetica-Bold'
)

body_style = ParagraphStyle(
    'CustomBody',
    parent=styles['BodyText'],
    fontSize=11,
    alignment=TA_JUSTIFY,
    spaceAfter=12,
    leading=16
)

bullet_style = ParagraphStyle(
    'BulletStyle',
    parent=styles['BodyText'],
    fontSize=11,
    leftIndent=20,
    spaceAfter=6,
    leading=14
)

code_block_style = ParagraphStyle(
    'CodeBlockStyle',
    parent=styles['BodyText'],
    fontSize=10,
    fontName='Courier',
    leftIndent=24,
    spaceAfter=10,
    leading=13
)

table_style = ParagraphStyle(
    'TableText',
    parent=styles['BodyText'],
    fontSize=10,
    alignment=TA_LEFT,
    spaceAfter=0
)


def get_roadmap_diagram_paths():
    """Return sorted rendered roadmap diagram paths for Section 18."""
    render_dir = Path(r'l:\bookstore\diagrams\rendered')
    patterns = [
        'roadmap-*.png',
        'roadmap-*.jpg',
        'roadmap-*.jpeg',
        'roadmap-*.svg',
    ]

    diagram_paths = []
    for pattern in patterns:
        diagram_paths.extend(render_dir.glob(pattern))

    # Deduplicate and sort for stable ordering in generated reports.
    return sorted(set(diagram_paths), key=lambda p: p.name.lower())

# Content
story = []

# Title Page
story.append(Spacer(1, 0.5*inch))
story.append(Paragraph("TECHNICAL REPORT", title_style))
story.append(Spacer(1, 12))
story.append(Paragraph("Bookstore Microservices Architecture", ParagraphStyle(
    'Subtitle',
    parent=styles['Normal'],
    fontSize=18,
    textColor=colors.HexColor('#1f4788'),
    alignment=TA_CENTER,
    spaceAfter=20
)))
story.append(Paragraph("Event-Driven Implementation with Django, FastAPI, and RabbitMQ", ParagraphStyle(
    'Subtitle2',
    parent=styles['Normal'],
    fontSize=12,
    textColor=colors.HexColor('#505050'),
    alignment=TA_CENTER,
    spaceAfter=30,
    fontName='Helvetica-Oblique'
)))

story.append(Spacer(1, 0.5*inch))

# Document info table
info_data = [
    ['Date:', f'{datetime.now().strftime("%B %d, %Y")}'],
    ['System Type:', 'Hybrid Monolith + Microservices'],
    ['Framework:', 'Django + FastAPI'],
    ['Message Broker:', 'RabbitMQ'],
    ['Container Orchestration:', 'Docker Compose'],
    ['Primary Language:', 'Python'],
]

info_table = Table(info_data, colWidths=[1.5*inch, 3.5*inch])
info_table.setStyle(TableStyle([
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, -1), 10),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ('TOPPADDING', (0, 0), (-1, -1), 8),
    ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2c5aa0')),
]))
story.append(info_table)

story.append(PageBreak())

# Abstract
story.append(Paragraph("Abstract", heading1_style))
story.append(Paragraph(
    "This report presents a production-ready microservices architecture for an e-commerce bookstore "
    "system utilizing a hybrid approach: a monolithic Django application for web UI and orchestration, "
    "combined with three independent FastAPI microservices for Payment, Shipping, and Notification processing. "
    "The system implements event-driven communication via RabbitMQ for asynchronous workflows, synchronous "
    "REST APIs for critical-path operations, and database-per-service isolation with PostgreSQL. "
    "The architecture achieves separation of concerns, independent scaling, graceful fault handling, and "
    "clear service boundaries following Domain-Driven Design principles. This report details the architectural "
    "design, service responsibilities, communication patterns, deployment model, and provides implementation "
    "walkthroughs for key business scenarios.",
    body_style
))
story.append(Spacer(1, 12))

# Keywords
story.append(Paragraph(
    "<b>Keywords:</b> microservices, Django REST Framework, FastAPI, RabbitMQ, event-driven architecture, "
    "API gateway design, database-per-service, Docker Compose, domain-driven design, e-commerce.",
    bullet_style
))
story.append(PageBreak())

# 1. Introduction
story.append(Paragraph("1. Introduction", heading1_style))

story.append(Paragraph("1.1 Background", heading2_style))
story.append(Paragraph(
    "Traditional monolithic e-commerce platforms face scaling challenges as business complexity grows. "
    "A single application instance managing user authentication, catalog browsing, shopping carts, payment processing, "
    "and shipment tracking creates resource contention and deployment risk. The Bookstore system addresses this by "
    "decomposing operational concerns into independent services while maintaining a centralized web interface through "
    "a Django monolith that orchestrates customer-facing workflows.",
    body_style
))

story.append(Paragraph("1.2 Problem Statement", heading2_style))
story.append(Paragraph(
    "A purely monolithic bookstore architecture presents several operational constraints:",
    body_style
))
problems = [
    "<b>Uneven resource utilization:</b> Payment and shipping operations require different computational profiles and availability SLOs than catalog browsing.",
    "<b>Deployment coupling:</b> Each update to payment logic forces redeployment of the entire system.",
    "<b>Technology constraints:</b> A single technology stack may not suit specialized workloads (e.g., real-time notifications).",
    "<b>Scaling granularity:</b> Scaling cannot target specific bottlenecks independently.",
    "<b>Team organization:</b> Tight coupling complicates parallel development across functional domains."
]
for problem in problems:
    story.append(Paragraph(problem, bullet_style))

story.append(Paragraph("1.3 Objective", heading2_style))
story.append(Paragraph(
    "This project implements a hybrid microservices architecture that balances pragmatism with architectural "
    "best practices. The solution maintains a monolithic web tier for customer UI and order orchestration while "
    "delegating payment, shipping, and notification concerns to dedicated FastAPI services. Event-driven communication "
    "decouples the notification service from transactional workloads, enabling eventual consistency and resilience.",
    body_style
))

story.append(PageBreak())

# 2. Architectural Overview
story.append(Paragraph("2. Architectural Overview", heading1_style))

story.append(Paragraph("2.1 System Topology", heading2_style))
story.append(Paragraph(
    "The system employs a hybrid architecture with the following components:",
    body_style
))

topology_data = [
    ['Component', 'Type', 'Purpose', 'Port'],
    ['Django Web App', 'Monolith', 'UI, authentication, cart, order orchestration', '8000'],
    ['Payment Service', 'FastAPI', 'Payment processing and refunds', '5000'],
    ['Shipping Service', 'FastAPI', 'Shipment creation and tracking', '5001'],
    ['Notification Service', 'FastAPI', 'Email notifications (event consumer)', '5002'],
    ['PostgreSQL', 'Database', '4 databases (bookstore, payment, shipping, notification)', '5432'],
    ['RabbitMQ', 'Message Broker', 'Asynchronous event distribution', '5672/15672'],
]

topology_table = Table(topology_data, colWidths=[1.2*inch, 1*inch, 2.2*inch, 0.8*inch])
topology_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, -1), 9),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ('TOPPADDING', (0, 0), (-1, -1), 8),
    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
]))
story.append(topology_table)
story.append(Spacer(1, 12))

story.append(Paragraph("2.2 Communication Patterns", heading2_style))
story.append(Paragraph(
    "The system implements two primary communication patterns:",
    body_style
))

story.append(Paragraph(
    "<b>Synchronous (HTTP/REST):</b> Used for critical-path operations requiring immediate responses "
    "(payment processing and shipment creation). Requests include bearer token authentication and implement "
    "timeouts for graceful degradation.",
    bullet_style
))

story.append(Paragraph(
    "<b>Asynchronous (RabbitMQ):</b> Used for notification workflows where loose coupling and eventual consistency "
    "are acceptable. The Notification Service subscribes to domain events published by Payment and Shipping services, "
    "enabling independent deployment and fault isolation.",
    bullet_style
))

story.append(Spacer(1, 6))

story.append(Paragraph("2.3 Database Architecture", heading2_style))
story.append(Paragraph(
    "Each service owns independent PostgreSQL databases, preventing cross-service schema coupling:",
    body_style
))

db_data = [
    ['Database', 'Service', 'Key Tables', 'Purpose'],
    ['bookstore', 'Django Monolith', 'users, orders, books, cart, customers', 'Web tier and order orchestration'],
    ['payment_service', 'Payment Service', 'payments, refunds', 'Payment transaction records'],
    ['shipping_service', 'Shipping Service', 'shipments', 'Shipment tracking'],
    ['notification_service', 'Notification Service', 'notifications', 'Notification audit trail'],
]

db_table = Table(db_data, colWidths=[1.2*inch, 1.2*inch, 1.5*inch, 1.7*inch])
db_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, -1), 9),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ('TOPPADDING', (0, 0), (-1, -1), 8),
    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
]))
story.append(db_table)

story.append(PageBreak())

# 3. Service Design
story.append(Paragraph("3. Service Design and Responsibilities", heading1_style))

story.append(Paragraph("3.1 Django Monolith", heading2_style))
story.append(Paragraph(
    "The Django application serves as the primary customer interface and orchestrator:",
    body_style
))

story.append(Paragraph("<b>Core Responsibilities:</b>", bullet_style))
responsibilities = [
    "User authentication (username/password with token generation)",
    "Book catalog management and search",
    "Shopping cart operations (add, view, update quantities)",
    "Order creation and status tracking",
    "Integration with external payment service (synchronous calls)",
    "Integration with external shipping service (synchronous calls)",
    "Event publishing for order creation and updates",
    "Staff management UI for shipment status updates"
]
for resp in responsibilities:
    story.append(Paragraph(resp, bullet_style))

story.append(Spacer(1, 6))
story.append(Paragraph("<b>Key Models:</b>", bullet_style))
models = [
    "User: username, email, password, authentication token",
    "Customer: user reference, loyalty points, registration date",
    "Book: ISBN, title, author, price, stock quantity",
    "Order: customer reference, total amount, status (pending/processing/completed/cancelled)",
    "CartItem: cart reference, book reference, quantity"
]
for model in models:
    story.append(Paragraph(model, bullet_style))

story.append(Paragraph("3.2 Payment Service", heading2_style))
story.append(Paragraph(
    "<b>Framework:</b> FastAPI 0.104.1 | <b>Port:</b> 5000 | <b>Database:</b> payment_service (PostgreSQL)",
    bullet_style
))

story.append(Paragraph("<b>Core Responsibilities:</b>", bullet_style))
payment_resp = [
    "Process payment transactions via Stripe API",
    "Manage payment status lifecycle (PENDING → PROCESSING → COMPLETED/FAILED)",
    "Handle refund requests and tracking",
    "Implement idempotency checking to prevent duplicate charges",
    "Publish 'order.paid' event to message broker on successful payment",
    "Provide payment status queries for order tracking"
]
for resp in payment_resp:
    story.append(Paragraph(resp, bullet_style))

story.append(Spacer(1, 6))
story.append(Paragraph("<b>API Endpoints:</b>", bullet_style))
endpoints = [
    "<b>POST /api/v1/payments/process</b> – Submit payment for processing",
    "<b>GET /api/v1/payments/{order_id}</b> – Retrieve payment status",
    "<b>POST /api/v1/payments/refund</b> – Request payment refund",
    "<b>GET /health</b> – Health check probe"
]
for ep in endpoints:
    story.append(Paragraph(ep, bullet_style))

story.append(Paragraph("3.3 Shipping Service", heading2_style))
story.append(Paragraph(
    "<b>Framework:</b> FastAPI 0.104.1 | <b>Port:</b> 5001 | <b>Database:</b> shipping_service (PostgreSQL)",
    body_style
))

story.append(Paragraph("<b>Core Responsibilities:</b>", bullet_style))
shipping_resp = [
    "Calculate shipping costs based on method and destination",
    "Create shipment records and assign tracking numbers",
    "Update shipment status through lifecycle (PENDING → PROCESSING → SHIPPED → DELIVERED/FAILED)",
    "Publish domain events (shipment.created, shipment.updated) to message broker",
    "Provide shipping options to customers (Standard $5, Express $15, Overnight $50)",
    "Track estimated delivery dates"
]
for resp in shipping_resp:
    story.append(Paragraph(resp, bullet_style))

story.append(Spacer(1, 6))
story.append(Paragraph("<b>Shipping Methods:</b>", bullet_style))
methods = [
    "Standard Shipping: $5 (5-7 business days)",
    "Express Shipping: $15 (2-3 business days)",
    "Overnight Shipping: $50 (next business day)"
]
for method in methods:
    story.append(Paragraph(method, bullet_style))

story.append(Paragraph("3.4 Notification Service", heading2_style))
story.append(Paragraph(
    "<b>Framework:</b> FastAPI 0.104.1 | <b>Port:</b> 5002 | <b>Database:</b> notification_service (PostgreSQL)",
    body_style
))

story.append(Paragraph("<b>Core Responsibilities:</b>", bullet_style))
notif_resp = [
    "Consume domain events from RabbitMQ (asynchronous worker)",
    "Generate and send email notifications based on event types",
    "Maintain notification audit trail in database",
    "Handle email delivery failures and retries",
    "Support both development (console logging) and production (SMTP) modes",
    "Implement automatic reconnection and error recovery"
]
for resp in notif_resp:
    story.append(Paragraph(resp, bullet_style))

story.append(Spacer(1, 6))
story.append(Paragraph("<b>Events Consumed:</b>", bullet_style))
events = [
    "order.paid – Sends order confirmation email to customer",
    "shipment.created – Sends shipping notification with tracking information",
    "shipment.updated – Sends status update emails for delivered/failed shipments"
]
for event in events:
    story.append(Paragraph(event, bullet_style))

story.append(PageBreak())

# 4. Order Processing Flow
story.append(Paragraph("4. End-to-End Order Processing Flow", heading1_style))

story.append(Paragraph("4.1 Complete Order Lifecycle", heading2_style))
story.append(Paragraph(
    "The following sequence diagram illustrates the complete order processing workflow from customer "
    "submission through shipment:",
    body_style
))

story.append(Spacer(1, 6))

flow_steps = [
    "1. Customer submits order through Django web interface with selected books and quantities.",
    "2. Order is validated and saved in bookstore database with status=PENDING.",
    "3. Django monolith calls Payment Service synchronously via HTTP POST /api/v1/payments/process.",
    "4. Payment Service processes payment with Stripe, updates payment record, and publishes order.paid event to RabbitMQ.",
    "5. Django receives payment confirmation and calls Shipping Service synchronously via HTTP POST /api/v1/shipping/create.",
    "6. Shipping Service creates shipment record, publishes shipment.created event to RabbitMQ.",
    "7. Order status is updated to PROCESSING in Django database.",
    "8. Client receives immediate confirmation with order and tracking details.",
    "9. [Asynchronously] Notification Service consumes order.paid event, sends order confirmation email.",
    "10. [Asynchronously] Notification Service consumes shipment.created event, sends shipping notification email with tracking.",
    "11. Notification records are persisted in notification_service database for audit trail."
]
for step in flow_steps:
    story.append(Paragraph(step, bullet_style))

story.append(Paragraph("4.2 Failure Handling", heading2_style))
story.append(Paragraph(
    "The system implements graceful degradation for service outages:",
    body_style
))

story.append(Paragraph(
    "<b>Payment Service Unavailable:</b> Request times out after 30 seconds; customer is notified and can retry. "
    "Transaction state is not corrupted.",
    bullet_style
))

story.append(Paragraph(
    "<b>Shipping Service Unavailable:</b> Order is marked for manual processing; staff can create shipment manually through UI. "
    "Customer receives partial confirmation.",
    bullet_style
))

story.append(Paragraph(
    "<b>Notification Service Unavailable:</b> Events remain in RabbitMQ queue and will be processed once service recovers. "
    "This does not affect order completion.",
    bullet_style
))

story.append(PageBreak())

# 5. Event-Driven Architecture
story.append(Paragraph("5. Event-Driven Architecture", heading1_style))

story.append(Paragraph("5.1 RabbitMQ Configuration", heading2_style))

config_data = [
    ['Property', 'Value', 'Purpose'],
    ['Message Broker', 'RabbitMQ 3', 'Asynchronous event distribution'],
    ['Exchange Type', 'Topic', 'Content-based routing of events'],
    ['Exchange Name', 'bookstore.events', 'Central event bus'],
    ['Queue Name', 'notification_service_queue', 'Notification service subscription'],
    ['Connection Port', '5672 (AMQP)', 'Inter-service communication'],
    ['Management UI', '15672 (HTTP)', 'Broker monitoring and admin'],
    ['Durability', 'Enabled', 'Messages survive broker restart'],
]

config_table = Table(config_data, colWidths=[1.3*inch, 1.2*inch, 2.2*inch])
config_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, -1), 9),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ('TOPPADDING', (0, 0), (-1, -1), 8),
    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
]))
story.append(config_table)

story.append(Spacer(1, 12))

story.append(Paragraph("5.2 Event Message Format", heading2_style))
story.append(Paragraph(
    "All domain events follow a consistent structure for interoperability:",
    body_style
))

story.append(Paragraph(
    "{ \"event_type\": \"order.paid\", \"timestamp\": \"2026-03-11T10:30:45Z\", "
    "\"correlation_id\": \"uuid-here\", \"data\": {\"order_id\": 123, \"amount\": 99.99, ...} }",
    ParagraphStyle('Code', parent=styles['Normal'], fontSize=9, fontName='Courier', 
                   leftIndent=20, rightIndent=20, backColor=colors.HexColor('#f5f5f5'), 
                   borderPadding=8, spaceAfter=12)
))

story.append(Paragraph("5.3 Published Events", heading2_style))

pub_events = [
    ("<b>order.paid</b> – Published by Payment Service after successful payment. Contains "
     "order_id, payment_id, amount, timestamp. Triggers order confirmation email."),
    ("<b>shipment.created</b> – Published by Shipping Service when shipment record is created. "
     "Contains order_id, shipment_id, tracking_number, estimated_delivery. Triggers shipping notification email."),
    ("<b>shipment.updated</b> – Published by Shipping Service on status changes (SHIPPED, DELIVERED, FAILED). "
     "Triggers customer status update emails.")
]

for event_desc in pub_events:
    story.append(Paragraph(event_desc, bullet_style))

story.append(PageBreak())

# 6. Deployment
story.append(Paragraph("6. Deployment and Infrastructure", heading1_style))

story.append(Paragraph("6.1 Docker Compose Orchestration", heading2_style))
story.append(Paragraph(
    "The system is containerized and orchestrated via Docker Compose for development and testing. "
    "Each service defines its own Dockerfile and runs independently within the Docker network.",
    body_style
))

story.append(Paragraph("<b>Services Managed by Docker Compose:</b>", bullet_style))
services = [
    "<b>web (Django):</b> Port 8000, hot reload enabled for development, depends on postgres and rabbitmq",
    "<b>payment-service (FastAPI):</b> Port 5000, auto-reload enabled, depends on postgres and rabbitmq",
    "<b>shipping-service (FastAPI):</b> Port 5001, auto-reload enabled, depends on postgres and rabbitmq",
    "<b>notification-service (FastAPI):</b> Port 5002, background RabbitMQ consumer, depends on rabbitmq",
    "<b>postgres:</b> Port 5432, PostgreSQL 14 database server for all services",
    "<b>rabbitmq:</b> Ports 5672 (AMQP) and 15672 (management UI)"
]
for svc in services:
    story.append(Paragraph(svc, bullet_style))

story.append(Spacer(1, 6))

story.append(Paragraph("6.2 Health Checks", heading2_style))
story.append(Paragraph(
    "All services implement health check endpoints that Docker Compose monitors:",
    body_style
))

story.append(Paragraph(
    "<b>GET /health</b> – Returns 200 OK if service is operational. Used by Docker to verify "
    "readiness before accepting traffic.",
    bullet_style
))

story.append(Paragraph("6.3 Quick Start", heading2_style))
story.append(Paragraph(
    "To run the complete system:",
    body_style
))

story.append(Paragraph("$ docker-compose up", ParagraphStyle('Code', parent=styles['Normal'], 
    fontSize=10, fontName='Courier', leftIndent=20, rightIndent=20, backColor=colors.HexColor('#f5f5f5'), 
    borderPadding=8, spaceAfter=6)))

story.append(Paragraph(
    "This command starts all services, applies database migrations, creates schema, and initializes RabbitMQ queues. "
    "The system is ready for testing after all health checks pass.",
    body_style
))

story.append(PageBreak())

# 7. Security
story.append(Paragraph("7. Security and Authentication", heading1_style))

story.append(Paragraph("7.1 Service-to-Service Authentication", heading2_style))
story.append(Paragraph(
    "Inter-service communication is authenticated using bearer tokens:",
    body_style
))

story.append(Paragraph(
    "All HTTP requests from Django monolith to Payment/Shipping services include an Authorization header "
    "with a bearer token. Services validate the token before processing requests. Each service has a unique token "
    "configured in environment variables.",
    bullet_style
))

story.append(Paragraph("7.2 Database Access Control", heading2_style))
story.append(Paragraph(
    "Each service connects to PostgreSQL using dedicated credentials with principle of least privilege:",
    body_style
))

story.append(Paragraph(
    "Services authenticate with PostgreSQL using username/password credentials over connection pooling. "
    "Network access is restricted within the Docker network (no external database access).",
    bullet_style
))

story.append(Paragraph("7.3 Message Broker Security", heading2_style))
story.append(Paragraph(
    "RabbitMQ access is controlled via username/password (default guest/guest for development). "
    "In production, strong credentials and TLS encryption would be required.",
    body_style
))

story.append(Paragraph("7.4 Recommended Security Enhancements", heading2_style))
enhancements = [
    "Implement JWT tokens for stateless authentication across services",
    "Add rate limiting and request throttling at the API Gateway (Django)",
    "Enable TLS/SSL for inter-service HTTP communication and RabbitMQ",
    "Implement request signing to prevent tampering",
    "Add comprehensive audit logging for sensitive operations",
    "Enable encryption at rest for database storage"
]
for enh in enhancements:
    story.append(Paragraph(enh, bullet_style))

story.append(PageBreak())

# 8. Scalability and Performance
story.append(Paragraph("8. Scalability and Performance Considerations", heading1_style))

story.append(Paragraph("8.1 Horizontal Scaling", heading2_style))
story.append(Paragraph(
    "Services can be scaled independently based on demand:",
    body_style
))

story.append(Paragraph(
    "<b>Catalog Browsing (Read-Heavy):</b> Scale Django and book-related queries independently. "
    "Implement caching to reduce database load.",
    bullet_style
))

story.append(Paragraph(
    "<b>Payment Processing (CPU/Network Intensive):</b> Scale Payment Service independently. "
    "Payment transactions block order flow, so throughput directly impacts customer experience.",
    bullet_style
))

story.append(Paragraph(
    "<b>Notifications (Queue-Based):</b> Scale Notification Service based on message backlog. "
    "This workload is decoupled and doesn't affect customer-facing operations.",
    bullet_style
))

story.append(Paragraph("8.2 Performance Optimization Strategies", heading2_style))
optimizations = [
    "Implement database connection pooling to reduce connection overhead",
    "Cache frequently accessed book data and catalog metadata",
    "Use read replicas for reporting and analytics queries",
    "Implement request/response compression for large payloads",
    "Add CDN for static assets (book cover images)",
    "Batch notification email sends for efficiency",
    "Use message acknowledgments to guarantee notification delivery"
]
for opt in optimizations:
    story.append(Paragraph(opt, bullet_style))

story.append(Paragraph("8.3 Monitoring and Observability", heading2_style))
story.append(Paragraph(
    "Production deployment should include:",
    body_style
))

story.append(Paragraph(
    "Distributed tracing (OpenTelemetry or Jaeger) to track requests across services and identify latency bottlenecks.",
    bullet_style
))

story.append(Paragraph(
    "Centralized logging (ELK stack or similar) for aggregating logs from all services.",
    bullet_style
))

story.append(Paragraph(
    "Metrics collection (Prometheus) and dashboards (Grafana) for service health, throughput, and error rates.",
    bullet_style
))

story.append(Paragraph(
    "Alerting thresholds for SLOs (e.g., payment processing latency < 5s, notification delivery success > 99%).",
    bullet_style
))

story.append(PageBreak())

# 9. Design Patterns and Principles
story.append(Paragraph("9. Design Patterns and Architectural Principles", heading1_style))

story.append(Paragraph("9.1 Applied Design Patterns", heading2_style))

patterns = [
    ("<b>Database per Service:</b> Each microservice owns independent database(s). Data sharing occurs through "
     "APIs and business identifiers (order_id, customer_id) rather than direct database joins."),
    ("<b>API Gateway Pattern:</b> Django monolith acts as primary entry point, aggregating calls to downstream services."),
    ("<b>Event-Driven Architecture:</b> Asynchronous events decouple critical services from ancillary workflows (notifications)."),
    ("<b>Circuit Breaker (implicit):</b> Service calls implement timeouts and graceful fallback on failure."),
    ("<b>Domain Events:</b> Services publish domain-specific events (order.paid, shipment.created) enabling loose coupling."),
    ("<b>Saga Pattern (manual):</b> Order processing coordinates multiple services through explicit orchestration."),
]

for pattern in patterns:
    story.append(Paragraph(pattern, bullet_style))

story.append(Paragraph("9.2 SOLID Principles", heading2_style))

solid = [
    ("<b>Single Responsibility:</b> Each service handles one business capability (payments, shipping, notifications). "
     "Models are focused on domain objects."),
    ("<b>Open/Closed:</b> Services are open for extension (new event types, shipping methods) but closed for modification "
     "of core logic."),
    ("<b>Liskov Substitution:</b> Payment processors can be swapped (Stripe → alternative providers) without changing "
     "service interface."),
    ("<b>Interface Segregation:</b> Services expose focused APIs (GET /payments/{id}, POST /shipments); clients use "
     "only required operations."),
    ("<b>Dependency Inversion:</b> Services depend on message broker abstraction for events, not concrete implementations."),
]

for principle in solid:
    story.append(Paragraph(principle, bullet_style))

story.append(Paragraph("9.3 Domain-Driven Design Elements", heading2_style))
story.append(Paragraph(
    "The system respects DDD principles:",
    body_style
))

ddd = [
    "<b>Bounded Contexts:</b> Payment Service, Shipping Service, and Notification Service each represent distinct business domains.",
    "<b>Ubiquitous Language:</b> Core terms (Order, Payment, Shipment) are used consistently across services and APIs.",
    "<b>Aggregates:</b> Order is the aggregate root for payment and shipment operations; Payment and Shipment are separate aggregates.",
    "<b>Domain Events:</b> Services publish events representing significant business occurrences (payment success, shipment creation).",
    "<b>Repository Pattern:</b> Each service manages its persistent entities through database abstraction layer."
]
for item in ddd:
    story.append(Paragraph(item, bullet_style))

story.append(PageBreak())

# 10. Deployment Walkthrough
story.append(Paragraph("10. Deployment and Operations Walkthrough", heading1_style))

story.append(Paragraph("10.1 Local Development Setup", heading2_style))

dev_steps = [
    "1. Clone repository and navigate to project root",
    "2. Ensure Docker Desktop is running",
    "3. Execute: docker-compose up",
    "4. Wait 10-15 seconds for database migrations to complete",
    "5. Verify all services are healthy: docker-compose ps",
    "6. Access Django at http://localhost:8000",
    "7. RabbitMQ management UI available at http://localhost:15672 (guest/guest)"
]
for step in dev_steps:
    story.append(Paragraph(step, bullet_style))

story.append(Paragraph("10.2 Testing the Complete Flow", heading2_style))
story.append(Paragraph(
    "To verify end-to-end functionality:",
    body_style
))

test_steps = [
    "1. Create a customer account via Django web UI (/customers/)",
    "2. Browse books and add items to shopping cart",
    "3. Submit order with payment information",
    "4. Observe payment processing and confirmation of payment.",
    "5. Verify shipment creation with tracking number",
    "6. Check notification service logs for email events published",
    "7. Observe final order status as COMPLETED in Django"
]
for step in test_steps:
    story.append(Paragraph(step, bullet_style))

story.append(Paragraph("10.3 Monitoring Event Processing", heading2_style))
story.append(Paragraph(
    "To observe asynchronous events:",
    body_style
))

story.append(Paragraph(
    "$ docker-compose logs -f notification-service",
    ParagraphStyle('Code', parent=styles['Normal'], fontSize=10, fontName='Courier', 
                   leftIndent=20, rightIndent=20, backColor=colors.HexColor('#f5f5f5'), 
                   borderPadding=8, spaceAfter=6)
))

story.append(Paragraph(
    "This displays real-time logs of the Notification Service consuming events from the message broker. "
    "Each order.paid and shipment event will be logged as it is processed.",
    body_style
))

story.append(PageBreak())

# 11. Testing
story.append(Paragraph("11. Testing Strategy", heading1_style))

story.append(Paragraph("11.1 Current Test Coverage", heading2_style))
story.append(Paragraph(
    "The system includes functional tests validating critical workflows:",
    body_style
))

story.append(Paragraph(
    "Integration tests verify end-to-end order processing including payment and shipping service calls. "
    "Tests exercise the complete flow from order creation through notification publishing. "
    "Services are tested both independently and in integration.",
    bullet_style
))

story.append(Paragraph("11.2 Recommended Test Matrix for Production", heading2_style))

test_matrix = [
    "<b>Unit Tests:</b> Model validation, business logic for price calculation, shipment cost computation",
    "<b>API Integration Tests:</b> Test each service endpoint with valid/invalid inputs, verify error handling",
    "<b>Contract Tests:</b> Verify service-to-service interfaces match expectations (payment API, shipping API)",
    "<b>End-to-End Tests:</b> Full order workflow from Django UI through notification delivery",
    "<b>Resilience Tests:</b> Verify graceful degradation when services are unavailable",
    "<b>Performance Tests:</b> Load test critical paths (order checkout, payment processing)",
    "<b>Security Tests:</b> Test authentication, authorization, input validation, SQL injection prevention"
]

for test in test_matrix:
    story.append(Paragraph(test, bullet_style))

story.append(Paragraph("11.3 Test Execution", heading2_style))
story.append(Paragraph(
    "Tests can be executed via pytest after system is running:",
    body_style
))

story.append(Paragraph(
    "$ docker-compose exec web pytest tests/ -v",
    ParagraphStyle('Code', parent=styles['Normal'], fontSize=10, fontName='Courier', 
                   leftIndent=20, rightIndent=20, backColor=colors.HexColor('#f5f5f5'), 
                   borderPadding=8, spaceAfter=12)
))

story.append(PageBreak())

# 12. Limitations and Future Improvements
story.append(Paragraph("12. Current Limitations and Future Roadmap", heading1_style))

story.append(Paragraph("12.1 Known Limitations", heading2_style))

limitations = [
    "<b>Synchronous Payment/Shipping:</b> Order processing blocks on external service calls. "
    "Future enhancement: convert to event-driven with eventual consistency and customer polling.",
    
    "<b>Limited Resilience Patterns:</b> Current timeouts are basic. Production requires circuit breakers, "
    "exponential backoff retries, and bulkhead isolation.",
    
    "<b>No Distributed Transactions:</b> Payment and shipment operations are not strictly ACID across services. "
    "Requires saga pattern implementation for failure recovery.",
    
    "<b>Monolith Remains SPOF:</b> Django application is the gateway for all customer operations. "
    "Future: implement API Gateway service for better isolation.",
    
    "<b>No Service Mesh:</b> Inter-service communication lacks sophisticated routing, load balancing, "
    "and mutual TLS. Consider Istio for production.",
    
    "<b>Manual Authentication:</b> Service-to-service auth uses static bearer tokens. Future: JWT with expiration, "
    "automatic rotation, and PKI infrastructure."
]

for limit in limitations:
    story.append(Paragraph(limit, bullet_style))

story.append(Paragraph("12.2 Evolution Roadmap", heading2_style))

story.append(Paragraph(
    "<b>Phase 1 (Current):</b> Functional microservices with Docker Compose, synchronous REST, basic event publishing.",
    bullet_style
))

story.append(Paragraph(
    "<b>Phase 2 (Near-term):</b> Add sophisticated resilience (circuit breaker, retries, bulkhead). "
    "Implement distributed tracing. Add comprehensive API documentation (OpenAPI/Swagger).",
    bullet_style
))

story.append(Paragraph(
    "<b>Phase 3 (Mid-term):</b> Event-driven order processing with sagas for failure recovery. "
    "Deploy API Gateway separate from web monolith. Add service mesh (Istio) for production networking.",
    bullet_style
))

story.append(Paragraph(
    "<b>Phase 4 (Long-term):</b> Implement CQRS pattern for read/write separation. Add polyglot storage "
    "(MongoDB for notifications, Redis for caching). Migrate web tier to separate frontend (React/Vue). "
    "Implement observability suite (Prometheus, Grafana, Jaeger).",
    bullet_style
))

story.append(PageBreak())

# 13. Discussion
story.append(Paragraph("13. Discussion", heading1_style))

story.append(Paragraph("13.1 Benefits Achieved", heading2_style))
story.append(Paragraph(
    "The current bookstore implementation demonstrates a pragmatic hybrid architecture: the Django application "
    "retains customer-facing orchestration while specialized FastAPI services handle payment, shipping, and "
    "notification concerns. This separation improves maintainability, keeps operational responsibilities explicit, "
    "and allows the team to evolve service boundaries incrementally rather than through a risky full rewrite.",
    body_style
))

story.append(Paragraph("13.2 Trade-offs", heading2_style))
story.append(Paragraph(
    "The architecture introduces cross-service network calls, duplicated operational concerns, and higher deployment "
    "complexity than a pure monolith. Those costs are acceptable for this system because payment and shipping already "
    "have distinct reliability and scaling needs, but they also require stronger observability, retry policies, and "
    "contract discipline than the current academic baseline provides.",
    body_style
))

story.append(Paragraph("13.3 Academic vs Production Gap", heading2_style))
story.append(Paragraph(
    "The present solution is suitable as a reference implementation and coursework artifact, but a production rollout "
    "would still require stronger authentication, secrets management, idempotent workflow handling, distributed tracing, "
    "and automated contract testing. The current codebase establishes the right service boundaries; the remaining work is "
    "primarily operational hardening rather than another major architectural redesign.",
    body_style
))

story.append(PageBreak())

# 14. Conclusion
story.append(Paragraph("14. Conclusion", heading1_style))

conclusion_text = """
The Bookstore microservices architecture successfully balances pragmatism with architectural best practices. 
By maintaining a monolithic web tier for customer interaction and order orchestration while delegating specialized 
workloads to independent FastAPI services, the system achieves clear separation of concerns and independent scalability.

The event-driven notification workflow demonstrates effective decoupling, enabling the Notification Service to evolve 
independently without impacting customer-facing operations. This hybrid approach avoids the operational complexity of 
a pure microservices architecture while capturing its benefits: independent deployment, targeted scaling, and team autonomy.

The implementation serves as both a functional e-commerce platform and a reference architecture for teams building 
modern Python-based distributed systems. With the roadmap enhancements outlined in Section 12, the system can scale 
to production workloads while maintaining the architectural clarity and maintainability that characterizes well-designed 
distributed systems.

The Docker Compose-based deployment model enables developers to understand and experiment with the system locally, 
while the explicit service boundaries and REST/event-based contracts provide clear paths to cloud-native deployment 
with orchestrators like Kubernetes.
"""

story.append(Paragraph(conclusion_text, body_style))

story.append(PageBreak())

# 15. Detailed Scenario Walkthroughs
story.append(Paragraph("15. Detailed Scenario Walkthroughs", heading1_style))

story.append(Paragraph("15.1 Order Submission and Payment", heading2_style))
story.append(Paragraph(
    "A customer completes checkout in the Django storefront, which creates the local order record and then invokes the "
    "Payment Service over HTTP for transactional authorization. On success, the order can transition to a paid state and "
    "continue to downstream fulfillment; on failure, the order remains visible for retry or cancellation handling.",
    body_style
))

story.append(Paragraph("15.2 Shipment Creation and Tracking", heading2_style))
story.append(Paragraph(
    "After payment succeeds, the web tier calls the Shipping Service to create a shipment using the order identifier and "
    "delivery details. Shipment status is owned by the shipping database, preserving service autonomy while still allowing "
    "the storefront to display tracking progress through a service client abstraction.",
    body_style
))

story.append(Paragraph("15.3 Event-Driven Notification Flow", heading2_style))
story.append(Paragraph(
    "Payment and shipping milestones are published as domain events through RabbitMQ. The Notification Service consumes "
    "those events asynchronously and records outbound notification activity, which decouples user messaging from the "
    "critical checkout path and prevents email delivery latency from blocking transactional operations.",
    body_style
))

story.append(Paragraph("15.4 Failure Handling Scenario", heading2_style))
story.append(Paragraph(
    "If payment succeeds but shipment creation fails, the architecture preserves enough separation to retry fulfillment "
    "without re-running payment authorization. This scenario highlights why explicit state transitions, timeout handling, "
    "and eventually compensating actions are required as the system moves closer to production readiness.",
    body_style
))

story.append(PageBreak())

# 16. Architecture Decision Records (ADR Summary)
story.append(Paragraph("16. Architecture Decision Records (ADR Summary)", heading1_style))

adr_items = [
    "<b>ADR-01: Retain Django as the orchestration layer.</b> The storefront already contains customer-facing workflows, so keeping it as the integration point avoids unnecessary frontend disruption while services are extracted.",
    "<b>ADR-02: Use database-per-service isolation.</b> Payment, shipping, and notification data remain independently owned to prevent schema coupling and to enable separate lifecycle management.",
    "<b>ADR-03: Combine synchronous REST with asynchronous events.</b> Immediate operations such as payment and shipment creation use HTTP, while non-critical notifications use RabbitMQ for loose coupling.",
    "<b>ADR-04: Containerize all components for local reproducibility.</b> Docker Compose provides a consistent development topology and makes the distributed architecture testable on a single workstation.",
]
for item in adr_items:
    story.append(Paragraph(item, bullet_style))

story.append(PageBreak())

# 17. Performance and Scalability Considerations
story.append(Paragraph("17. Performance and Scalability Considerations", heading1_style))

story.append(Paragraph("17.1 Read-heavy vs Write-heavy Paths", heading2_style))
story.append(Paragraph(
    "Catalog browsing and book discovery remain comparatively read-heavy, while payment processing and shipment creation "
    "are write-heavy and latency-sensitive. Separating those concerns allows future scaling policies to target the real "
    "bottlenecks rather than scaling the entire application uniformly.",
    body_style
))

story.append(Paragraph("17.2 Latency Hotspots", heading2_style))
story.append(Paragraph(
    "The main latency hotspots are synchronous service-to-service calls from the Django application to payment and shipping, "
    "plus downstream event propagation for notifications. Timeouts, connection pooling, and structured retry policies are "
    "therefore more important than raw CPU scaling for the current deployment profile.",
    body_style
))

story.append(Paragraph("17.3 Data Growth", heading2_style))
story.append(Paragraph(
    "Order, payment, shipment, and notification records will all grow over time at different rates. Independent databases "
    "make archival, indexing, and retention policies easier to tune per domain, especially once notification history and "
    "operational audit logs become materially larger than core catalog data.",
    body_style
))

story.append(PageBreak())

# 18. Roadmap (Iteration Plan)
story.append(Paragraph("18. Roadmap (Iteration Plan)", heading1_style))

roadmap_items = [
    "<b>Iteration 1 - Security hardening:</b> Add stronger service authentication, centralize secret management, and enforce authorization checks at integration boundaries.",
    "<b>Iteration 2 - Reliability improvements:</b> Introduce retries, idempotency safeguards, circuit breakers, and better health/readiness reporting across all services.",
    "<b>Iteration 3 - Workflow maturity:</b> Expand event-driven orchestration for order lifecycle transitions and formalize compensating actions for partial failure scenarios.",
    "<b>Iteration 4 - Operational productization:</b> Add tracing, metrics dashboards, CI/CD validation, and production-grade deployment patterns beyond local Docker Compose.",
]
for item in roadmap_items:
    story.append(Paragraph(item, bullet_style))

story.append(Paragraph("18.1 Roadmap Architecture Diagrams", heading2_style))

diagram_paths = get_roadmap_diagram_paths()
if diagram_paths:
    story.append(Paragraph(
        "The roadmap is illustrated through multiple architecture diagrams, aligned with the staged evolution plan.",
        body_style
    ))
    for index, diagram_path in enumerate(diagram_paths, start=1):
        story.append(Paragraph(f"Figure 18.{index}: {diagram_path.stem}", bullet_style))
        story.append(Image(str(diagram_path), width=6.3 * inch, height=3.6 * inch))
        story.append(Spacer(1, 10))
else:
    story.append(Paragraph(
        "No rendered roadmap diagrams were found in diagrams/rendered. "
        "Render your PUML files to images named roadmap-*.png (or .jpg/.jpeg/.svg) to include them automatically.",
        body_style
    ))

story.append(PageBreak())

# Appendix A - Service List
story.append(Paragraph("Appendix A - Service List", heading1_style))

appendix_service_docs = [
    {
        "name": "api-gateway",
        "get_endpoint": "/books/",
        "get_desc": "List books through gateway UI.",
        "post_endpoint": "/books/",
        "post_desc": "Create a book through gateway.",
        "request": '{\n "title": "Clean Architecture",\n "author": "Robert C. Martin",\n "price": "19.99",\n "stock": 20\n}',
    },
    {
        "name": "customer-service",
        "get_endpoint": "/customers/",
        "get_desc": "Get all customers.",
        "post_endpoint": "/customers/",
        "post_desc": "Create customer.",
        "request": '{\n "name": "Alice",\n "email": "alice@example.com"\n}',
    },
    {
        "name": "staff-service",
        "get_endpoint": "/staffs/",
        "get_desc": "List staff records.",
        "post_endpoint": "/staffs/",
        "post_desc": "Create staff record.",
        "request": '{\n "name": "Staff One",\n "email": "staff1@example.com",\n "role": "inventory"\n}',
    },
    {
        "name": "manager-service",
        "get_endpoint": "/managers/",
        "get_desc": "List managers.",
        "post_endpoint": "/managers/",
        "post_desc": "Create manager.",
        "request": '{\n "name": "Manager One",\n "email": "manager1@example.com"\n}',
    },
    {
        "name": "catalog-service",
        "get_endpoint": "/catalogs/",
        "get_desc": "List catalogs.",
        "post_endpoint": "/catalogs/",
        "post_desc": "Create catalog.",
        "request": '{\n "name": "Software Engineering",\n "description": "Books for software practitioners"\n}',
    },
    {
        "name": "book-service",
        "get_endpoint": "/books/",
        "get_desc": "List books.",
        "post_endpoint": "/books/",
        "post_desc": "Create a book.",
        "request": '{\n "title": "Domain-Driven Design",\n "author": "Eric Evans",\n "price": "35.00",\n "stock": 12\n}',
    },
    {
        "name": "cart-service",
        "get_endpoint": "/carts/",
        "get_desc": "List carts.",
        "post_endpoint": "/cart-items/",
        "post_desc": "Add item into cart.",
        "request": '{\n "cart": 1,\n "book_id": 2,\n "quantity": 1\n}',
    },
    {
        "name": "order-service",
        "get_endpoint": "/orders/",
        "get_desc": "List orders.",
        "post_endpoint": "/orders/",
        "post_desc": "Create order.",
        "request": '{\n "customer_id": 1,\n "status": "pending"\n}',
    },
    {
        "name": "pay-service",
        "get_endpoint": "/payments/",
        "get_desc": "List payments.",
        "post_endpoint": "/payments/",
        "post_desc": "Create payment.",
        "request": '{\n "order_id": 1,\n "amount": "59.99",\n "status": "paid"\n}',
    },
    {
        "name": "ship-service",
        "get_endpoint": "/shipments/",
        "get_desc": "List shipments.",
        "post_endpoint": "/shipments/",
        "post_desc": "Create shipment.",
        "request": '{\n "order_id": 1,\n "address": "123 Main Street",\n "status": "created"\n}',
    },
    {
        "name": "comment-rate-service",
        "get_endpoint": "/comment-rates/",
        "get_desc": "List comments and ratings.",
        "post_endpoint": "/comment-rates/",
        "post_desc": "Create a comment/rating.",
        "request": '{\n "customer_id": 1,\n "book_id": 2,\n "comment": "Great read",\n "rating": 5\n}',
    },
    {
        "name": "recommender-ai-service",
        "get_endpoint": "/recommendations/",
        "get_desc": "List recommendations.",
        "post_endpoint": "/recommendations/",
        "post_desc": "Save recommendation score.",
        "request": '{\n "customer_id": 1,\n "book_id": 2,\n "score": 0.93\n}',
    },
]

for index, service in enumerate(appendix_service_docs, start=1):
    story.append(Paragraph(f"{index}. {service['name']}", heading2_style))
    story.append(Paragraph(f"Base path: `http://{service['name']}:8000`", body_style))
    story.append(Paragraph(
        f"<b>GET {service['get_endpoint']}</b> - Description: {service['get_desc']}",
        body_style
    ))
    story.append(Paragraph(
        f"<b>POST {service['post_endpoint']}</b> - Description: {service['post_desc']}",
        body_style
    ))
    story.append(Paragraph("* Request:", body_style))
    story.append(Paragraph(service['request'].replace("\n", "<br/>"), code_block_style))

story.append(Spacer(1, 12))

story.append(Paragraph(
    f"<i>Document generated: {datetime.now().strftime('%B %d, %Y at %H:%M:%S')}</i>",
    ParagraphStyle('Footer', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER, 
                   textColor=colors.grey)
))

# Build PDF
doc.build(story)

print(f"✓ Technical report generated successfully!")
print(f"✓ Location: {pdf_path}")
print(f"✓ Total sections: 18 major sections aligned to the example report structure")
