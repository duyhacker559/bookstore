# 03 - Apply RAG for Consulting Chat

## Objective

Build RAG chat that can:
- answer customer questions with citation
- propose products based on user intent and behavior signals
- avoid hallucination by grounding on KB

## RAG architecture

1. Query understanding
- detect intent: policy, product discovery, recommendation, order support
- extract filters: category, budget, size, genre, brand

2. Retrieval
- hybrid retrieval:
  - semantic vector search
  - keyword search for exact terms
- metadata filtering by category, language, stock_status

3. Re-ranking
- cross-encoder reranker for Top-20 to Top-5

4. Generation
- prompt with:
  - system rules
  - retrieved chunks with source ids
  - user context
- LLM returns answer plus cited sources

## Prompt policy

Must enforce:
- if no evidence, say not enough data
- do not invent policy or price
- always provide short recommendation rationale

## API contract

Create rag-service endpoints:
- GET /health
- POST /api/v1/chat/query
- POST /api/v1/chat/stream
- POST /api/v1/chat/feedback

Request example:
```json
{
  "session_id": "sess-001",
  "user_id": 123,
  "question": "Toi can mua sach hoc Python cho nguoi moi bat dau",
  "context": {
    "budget_max": 20,
    "preferred_category": "technology"
  }
}
```

Response example:
```json
{
  "answer": "Ban co the xem 3 dau sach sau...",
  "citations": ["chunk_129", "chunk_445"],
  "recommended_products": [101, 205, 309]
}
```

## Evaluation

Offline:
- retrieval recall@k
- grounded answer rate
- factual consistency score

Online:
- chat completion rate
- recommendation click-through rate
- conversion uplift

## Failure handling

- retrieval empty -> fallback to safe clarification question
- LLM timeout -> return concise fallback with top products
- low confidence -> ask follow-up constraints

## Integration in Django frontend

1. Add chatbot widget on:
- homepage
- product list page
- cart page

2. Backend proxy endpoint in monolith:
- POST /ai/chat

3. Log conversation traces with pii-safe policy
