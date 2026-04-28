# 04 - Deploy and Integrate into E-commerce System

## Objective

Deploy AI services and integrate with existing dockerized bookstore system.

## New services to add

1. behavior-service (FastAPI)
2. rag-service (FastAPI)
3. vector-db (Qdrant or pgvector)
4. optional model-registry (MLflow)

## Docker compose extension

Add to docker-compose.yml:
- behavior-service on port 5004
- rag-service on port 5005
- qdrant on port 6333

Required env vars for web service:
- BEHAVIOR_SERVICE_URL=http://behavior-service:5004
- BEHAVIOR_SERVICE_TOKEN=behavior-service-token-123
- RAG_SERVICE_URL=http://rag-service:5005
- RAG_SERVICE_TOKEN=rag-service-token-123

## Django integration points

1. Create clients
- store/behavior_client.py
- store/rag_client.py

2. Add API endpoints in monolith
- POST /ai/recommend
- POST /ai/chat

3. UI integration
- recommendation carousel on homepage and PDP
- chatbot panel in bottom-right

## Event integration via RabbitMQ

Publish behavior events from monolith:
- user.viewed_product
- user.added_to_cart
- user.completed_purchase

behavior-service consumes these events to keep near-real-time user state.

## Observability

1. Logs
- structured json logs with request_id and user_id_hash

2. Metrics
- latency p50, p95
- retrieval hit rate
- recommendation CTR
- chat success rate

3. Alerts
- health check failure
- response timeout spike
- model confidence collapse

## Security

- service-to-service bearer tokens
- rate limit public chat endpoint
- redact PII in logs and prompts

## Deployment steps

1. Build images
2. Run migrations for AI service databases
3. Start vector DB
4. Start behavior-service and rag-service
5. Run KB ingestion job
6. Smoke test APIs
7. Enable frontend widget flags

## Rollback plan

- Disable feature flag AI_CHAT_ENABLED and AI_RECOMMEND_ENABLED
- Route to deterministic recommendation fallback
- Keep checkout flow independent from AI services
