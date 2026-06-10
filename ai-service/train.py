from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import torch
from torch import nn

from lstm_model import LSTMRecommender, ProductVocabulary, pad_sequence


@dataclass
class LSTMArtifacts:
    model: LSTMRecommender
    vocabulary: ProductVocabulary
    product_catalog: List[Dict[str, object]]


def build_vocabulary(product_catalog: List[Dict[str, object]]) -> ProductVocabulary:
    product_ids = sorted({int(item["product_id"]) for item in product_catalog if item.get("product_id") is not None})
    product_to_idx = {product_id: index + 2 for index, product_id in enumerate(product_ids)}
    idx_to_product = {index: product_id for product_id, index in product_to_idx.items()}
    return ProductVocabulary(product_to_idx=product_to_idx, idx_to_product=idx_to_product)


def group_events_by_user(events: Iterable[Dict[str, object]]) -> Dict[int, List[Dict[str, object]]]:
    grouped: Dict[int, List[Dict[str, object]]] = {}
    for event in events:
        user_id = int(event["user_id"])
        grouped.setdefault(user_id, []).append(event)
    for user_id in grouped:
        grouped[user_id].sort(key=lambda item: str(item.get("timestamp") or ""))
    return grouped


def build_training_pairs(
    events: Iterable[Dict[str, object]],
    vocabulary: ProductVocabulary,
    sequence_length: int,
) -> Tuple[torch.Tensor, torch.Tensor]:
    grouped = group_events_by_user(events)
    sequences: List[List[int]] = []
    targets: List[int] = []

    for user_events in grouped.values():
        product_sequence = [vocabulary.encode(int(event["product_id"])) for event in user_events if int(event.get("product_id") or 0) > 0]
        if len(product_sequence) < 2:
            continue

        for index in range(1, len(product_sequence)):
            window = product_sequence[max(0, index - sequence_length) : index]
            sequences.append(pad_sequence(window, sequence_length))
            targets.append(product_sequence[index])

    if not sequences:
        empty_x = torch.zeros((0, sequence_length), dtype=torch.long)
        empty_y = torch.zeros((0,), dtype=torch.long)
        return empty_x, empty_y

    x = torch.tensor(sequences, dtype=torch.long)
    y = torch.tensor(targets, dtype=torch.long)
    return x, y


def train_lstm_model(
    events: Iterable[Dict[str, object]],
    product_catalog: List[Dict[str, object]],
    sequence_length: int = 5,
    embedding_dim: int = 64,
    hidden_dim: int = 96,
    lstm_layers: int = 1,
    epochs: int = 8,
    learning_rate: float = 0.01,
    checkpoint_path: str | None = None,
) -> LSTMArtifacts:
    vocabulary = build_vocabulary(product_catalog)
    x_train, y_train = build_training_pairs(events, vocabulary, sequence_length)

    model = LSTMRecommender(vocab_size=vocabulary.size, embedding_dim=embedding_dim, hidden_dim=hidden_dim, lstm_layers=lstm_layers)

    if len(x_train) > 0:
        optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
        criterion = nn.CrossEntropyLoss()
        model.train()
        for _ in range(max(1, epochs)):
            optimizer.zero_grad()
            logits = model(x_train)
            loss = criterion(logits, y_train)
            loss.backward()
            optimizer.step()

    if checkpoint_path:
        checkpoint = {
            "model_state_dict": model.state_dict(),
            "product_to_idx": vocabulary.product_to_idx,
            "product_catalog": product_catalog,
            "sequence_length": sequence_length,
            "embedding_dim": embedding_dim,
            "hidden_dim": hidden_dim,
            "lstm_layers": lstm_layers,
        }
        Path(checkpoint_path).parent.mkdir(parents=True, exist_ok=True)
        torch.save(checkpoint, checkpoint_path)

    return LSTMArtifacts(model=model, vocabulary=vocabulary, product_catalog=product_catalog)


def load_trained_lstm(checkpoint_path: str) -> LSTMArtifacts | None:
    checkpoint_file = Path(checkpoint_path)
    if not checkpoint_file.exists():
        return None

    checkpoint = torch.load(checkpoint_file, map_location="cpu")
    product_to_idx = {int(key): int(value) for key, value in checkpoint["product_to_idx"].items()}
    idx_to_product = {int(value): int(key) for key, value in product_to_idx.items()}
    vocabulary = ProductVocabulary(product_to_idx=product_to_idx, idx_to_product=idx_to_product)
    model = LSTMRecommender(
        vocab_size=vocabulary.size,
        embedding_dim=int(checkpoint.get("embedding_dim", 64)),
        hidden_dim=int(checkpoint.get("hidden_dim", 96)),
        lstm_layers=int(checkpoint.get("lstm_layers", 1)),
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    return LSTMArtifacts(model=model, vocabulary=vocabulary, product_catalog=list(checkpoint.get("product_catalog", [])))
