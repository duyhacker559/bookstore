from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence

import torch
from torch import nn


PAD_TOKEN = 0
UNK_TOKEN = 1


@dataclass
class ProductVocabulary:
    product_to_idx: Dict[int, int]
    idx_to_product: Dict[int, int]
    pad_idx: int = PAD_TOKEN
    unk_idx: int = UNK_TOKEN

    @property
    def size(self) -> int:
        return len(self.product_to_idx) + 2

    def encode(self, product_id: int) -> int:
        return self.product_to_idx.get(int(product_id), self.unk_idx)

    def decode(self, index: int) -> int:
        if index in self.idx_to_product:
            return self.idx_to_product[index]
        return -1


class LSTMRecommender(nn.Module):
    def __init__(self, vocab_size: int, embedding_dim: int = 64, hidden_dim: int = 96, lstm_layers: int = 1):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=PAD_TOKEN)
        self.lstm = nn.LSTM(
            input_size=embedding_dim,
            hidden_size=hidden_dim,
            num_layers=lstm_layers,
            batch_first=True,
        )
        self.classifier = nn.Linear(hidden_dim, vocab_size)

    def forward(self, tokens: torch.Tensor) -> torch.Tensor:
        embedded = self.embedding(tokens)
        output, _ = self.lstm(embedded)
        last_state = output[:, -1, :]
        return self.classifier(last_state)


def pad_sequence(sequence: Sequence[int], sequence_length: int) -> List[int]:
    trimmed = list(sequence)[-sequence_length:]
    padding = [PAD_TOKEN] * max(0, sequence_length - len(trimmed))
    return padding + trimmed


def softmax_top_k(logits: torch.Tensor, vocab: ProductVocabulary, top_k: int) -> List[Dict[str, float]]:
    probabilities = torch.softmax(logits, dim=-1).detach().cpu().tolist()
    ranked = []
    for index, probability in enumerate(probabilities):
        product_id = vocab.decode(index)
        if product_id <= 0:
            continue
        ranked.append({"product_id": product_id, "score": float(probability)})
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[: max(1, top_k)]
