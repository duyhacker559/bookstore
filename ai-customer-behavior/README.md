# AI Customer Behavior and Consulting Chat for Store

This folder contains implementation guides and execution logs for 5 deliverables:

1. model_behavior based on Deep Learning
2. Knowledge Base for consulting
3. RAG-based consulting chat
4. Deploy and integration into e-commerce system
5. AI chatbot for product recommendation

## Folder layout

- building/: one build guide per deliverable
- logs/: one execution log template per deliverable

## Build order

1. building/01_model_behavior_deep_learning.md
2. building/02_knowledge_base.md
3. building/03_rag_consulting_chat.md
4. building/04_deploy_integration_ecommerce.md
5. building/05_ai_chatbot_product_recommendation.md

## Suggested new services

- behavior-service (FastAPI): online scoring + recommendation API
- rag-service (FastAPI): retrieval + answer generation API
- vector-db (Qdrant or pgvector): document embeddings store

## Existing system integration points

- Django monolith: store/events.py, checkout and product pages
- payment-service, shipping-service, notification-service for event stream
- RabbitMQ for asynchronous behavior events
- PostgreSQL for user/profile/order data

## Quick start command set

```bash
# Start existing stack first
docker compose up -d --build

# Later after adding AI services, run full stack
docker compose up -d --build web payment-service shipping-service notification-service behavior-service rag-service ai-behavior-service
```

## Definition of done

- model_behavior can predict next best category and purchase propensity
- KB has ingestion, chunking, embedding, and metadata filtering
- RAG chat returns grounded answers with citations
- AI services are deployed in docker-compose and pass health checks
- chatbot can answer and recommend products in real time

## Applied to this project

Implemented artifacts in this repository:

- New service: behavior-service (port 5004)
- New service: rag-service (port 5005)
- New service: ai-behavior-service (port 5006)
- Django clients: store/behavior_client.py and store/rag_client.py
- Django API gateway endpoints:
	- POST /api/ai/recommend/
	- POST /api/ai/chat/
- docker-compose integrated with web environment variables and health checks

## AI Behavior Service (new)

Location: ai-customer-behavior/service

Core capabilities:
- Persist user behavior events in SQLite (click, search, addCart, checkout, purchase)
- Train a deep model (MLP) to estimate purchase propensity
- Build knowledge graph from user behavior
- Graph neural network style message passing to score category trends
- RAG retrieval from the knowledge graph for recommendations and analysis
- Gemini-based chatbot endpoint for customer consulting

Main API endpoints:
- POST /api/v1/ai/events
- POST /api/v1/ai/events/batch
- POST /api/v1/ai/train
- POST /api/v1/ai/graph/rebuild
- POST /api/v1/ai/rag/query
- POST /api/v1/ai/recommend
- POST /api/v1/ai/trends
- GET /api/v1/ai/alerts
- POST /api/v1/ai/chat

Monolith gateway endpoints (Django):
- POST /api/ai/advanced/events/
- POST /api/ai/advanced/train/
- POST /api/ai/advanced/recommend/
- POST /api/ai/advanced/chat/
- GET /api/ai/advanced/trends/
- GET /api/ai/advanced/alerts/

Customer/staff widget endpoints:
- POST /customer/ai/chat/
- POST /customer/ai/recommend/
- POST /customer/ai/train/ (staff only)

Feature flag:
- AI_ADVANCED_WIDGET_ENABLED=True to route customer widget to ai-behavior-service

Auth:
- Authorization: Bearer ai-behavior-service-token-123

Generated DOCX outputs:

- ai-customer-behavior/docx/01_model_behavior_deep_learning.docx
- ai-customer-behavior/docx/02_knowledge_base.docx
- ai-customer-behavior/docx/03_rag_consulting_chat.docx
- ai-customer-behavior/docx/04_deploy_integration_ecommerce.docx
- ai-customer-behavior/docx/05_ai_chatbot_product_recommendation.docx
- ai-customer-behavior/docx/AI_BUILD_SYSTEM_MASTER.docx

## Run and test in this project

1. Start services:

```bash
docker compose up -d --build web behavior-service rag-service ai-behavior-service
```

2. Open web app and login:

- http://localhost:8000

3. Test chatbot widget:

- Click the AI floating button in bottom-right
- Ask for product consulting or recommendations

4. Test API directly (session authenticated endpoint):

- POST /customer/ai/chat/
- POST /customer/ai/recommend/
