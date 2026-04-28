# 01 - Build model_behavior with Deep Learning

## Objective

Create model_behavior that learns customer behavior and predicts:
- next best product category
- purchase propensity score
- expected basket value band

## Input data schema

Use these sources from bookstore database and services:

1. User profile
- user_id
- age_band
- location
- account_age_days

2. Interaction events
- view_product
- add_to_cart
- remove_from_cart
- checkout_start
- purchase_completed
- review_submitted

3. Transaction history
- order_id
- timestamp
- category
- quantity
- amount
- payment_status
- shipping_method

4. Catalog metadata
- product_id
- category
- price_band
- stock_status
- tags

## Feature engineering

1. Sequential features
- recent N events as ordered sequence
- time delta between events

2. Aggregated features
- recency, frequency, monetary (RFM)
- category affinity distribution
- average order value
- discount sensitivity

3. Context features
- day_of_week, hour_slot
- campaign source

## Model architecture

Recommended baseline:
- Embedding layers for categorical ids
- Transformer encoder for event sequence
- Dense tower for static features
- Multi-task output heads:
  - head A: category classification (softmax)
  - head B: purchase probability (sigmoid)
  - head C: basket value band (softmax)

Loss:
- total_loss = w1 * CE_category + w2 * BCE_purchase + w3 * CE_value_band

## Training pipeline

1. Build dataset in parquet from PostgreSQL snapshots
2. Split by time:
- train: oldest 70%
- val: next 15%
- test: newest 15%
3. Normalize numeric features
4. Train with early stopping and model checkpoint
5. Export model to ONNX or TorchScript for serving

## Metrics

- Category head: Top-1, Top-3 accuracy
- Purchase head: AUC, PR-AUC, F1
- Value head: macro F1
- Business KPI: uplift in click-through rate and conversion

## Serving design

Create new service behavior-service:

Endpoints:
- GET /health
- POST /api/v1/behavior/score
- POST /api/v1/behavior/recommend
- POST /api/v1/behavior/feedback

Example score payload:
```json
{
  "user_id": 123,
  "session_events": ["view_book", "add_cart_book"],
  "context": {"hour": 20, "device": "mobile"}
}
```

## Integration with existing bookstore

1. In Django monolith add behavior client:
- store/behavior_client.py

2. Trigger scoring at:
- homepage load
- product detail view
- cart page

3. Store predictions for monitoring:
- table: behavior_predictions

## Retraining strategy

- Daily incremental data build
- Weekly full retraining
- Champion vs challenger evaluation before promote

## Risks and controls

- Data leakage: enforce time-based split
- Cold start users: fallback to popularity + content rules
- Drift: monitor feature drift and output confidence
