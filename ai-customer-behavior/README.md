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

## Current AI service

- ai-service (FastAPI): unified recommendation + chat API

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
docker compose up -d --build web payment-service shipping-service notification-service ai-service
```

## Definition of done

- model_behavior can predict next best category and purchase propensity
- KB has ingestion, chunking, embedding, and metadata filtering
- RAG chat returns grounded answers with citations
- AI services are deployed in docker-compose and pass health checks
- chatbot can answer and recommend products in real time

## Applied to this project

Implemented artifacts in this repository:

- New service: ai-service (port 5006)
- Django client: store/ai_service_client.py
- Django API gateway endpoints:
	- POST /api/ai/recommend/
	- POST /api/ai/chat/
- docker-compose integrated with web environment variables and health checks

## Legacy note

The previous behavior-service, rag-service, and ai-behavior-service have been removed.

Core capabilities:
- Persist user behavior events in SQLite (click, search, addCart, checkout, purchase)
- Train a deep model (MLP) to estimate purchase propensity
- Build knowledge graph from user behavior
- Graph neural network style message passing to score category trends
- RAG retrieval from the knowledge graph for recommendations and analysis
- Gemini-based chatbot endpoint for customer consulting

This legacy service has been replaced by the unified ai-service.

Current endpoints are provided by ai-service:
- POST /api/v1/recommend
- POST /api/v1/chatbot

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
docker compose up -d --build web ai-service
```

2. Open web app and login:

- http://localhost:8000

3. Test chatbot widget:

- Click the AI floating button in bottom-right
- Ask for product consulting or recommendations

4. Test API directly (session authenticated endpoint):

- POST /customer/ai/chat/
- POST /customer/ai/recommend/
