# 05 - AI Chatbot for Product Recommendation

## Objective

Attach AI chatbot to current e-commerce flow to provide product recommendations personalized by behavior model and RAG context.

## Recommendation strategy

Use a hybrid ranker:

final_score =
- 0.40 * behavior_model_score
- 0.30 * semantic_match_score
- 0.20 * popularity_trend_score
- 0.10 * margin_or_business_priority

## Chat to recommend pipeline

1. User asks question in chat
2. RAG detects intent and constraints
3. behavior-service returns user preference scores
4. candidate generation from catalog
5. rank and diversify candidates
6. return top-N products with reason

## Candidate generation

- content-based from embeddings
- collaborative patterns from similar users
- rule-based fallback for cold start

## Response format

Each recommendation item should include:
- product_id
- title
- price
- reason_for_recommendation
- confidence

## UX rules

- maximum 3 to 5 products per answer
- include one short reason per product
- ask one clarification if confidence < threshold

## Guardrails

- do not recommend out-of-stock items
- respect user budget and category constraints
- do not claim unsupported features

## A/B testing

Experiment groups:
- control: popularity-based recommendation
- variant A: behavior model only
- variant B: behavior + RAG hybrid

Track:
- CTR on suggested products
- add-to-cart rate
- order conversion rate
- average order value delta

## Integration checklist

1. Add chatbot widget in Django templates
2. Add backend proxy endpoints
3. Connect to rag-service and behavior-service
4. Add recommendation explanation rendering
5. Add telemetry events

## Production readiness

- latency target under 1.5s for non-streaming reply
- graceful fallback within 300ms if AI service unavailable
- full audit trail for recommendation decisions
