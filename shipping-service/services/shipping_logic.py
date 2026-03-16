"""Core shipping calculation logic."""

SHIPPING_METHODS = {
    "standard": {"name": "Standard Shipping", "base_fee": 5.0, "estimated_days": 5},
    "express": {"name": "Express Shipping", "base_fee": 15.0, "estimated_days": 2},
    "overnight": {"name": "Overnight Shipping", "base_fee": 30.0, "estimated_days": 1},
}


def get_shipping_method(method_code: str) -> dict:
    if method_code not in SHIPPING_METHODS:
        raise ValueError(f"Unsupported shipping method: {method_code}")
    return SHIPPING_METHODS[method_code]


def get_shipping_options(weight: float = 1.0) -> list[dict]:
    options = []
    weight_fee = max(weight, 0) * 1.5
    for code, meta in SHIPPING_METHODS.items():
        options.append(
            {
                "code": code,
                "name": meta["name"],
                "fee": round(meta["base_fee"] + weight_fee, 2),
                "estimated_days": meta["estimated_days"],
            }
        )
    return options
