from __future__ import annotations

from typing import Dict, List

from store.models.category.category import Category


DEFAULT_PRODUCT_CATEGORIES: List[str] = [
    "Fiction",
    "Science",
    "History",
    "Biography",
    "Children",
    "Fantasy",
    "Mystery",
    "Romance",
    "Technology",
    "Lifestyle",
    "Business",
    "Health",
    "Electronics",
    "Mobile",
    "Home Appliance",
    "Beauty",
    "Food",
    "Furniture",
    "Sports",
    "Toys",
]


def ensure_minimum_product_categories(min_count: int = 10) -> Dict[str, int]:
    min_count = max(int(min_count), 0)
    existing_names = {name.casefold() for name in Category.objects.values_list("name", flat=True)}
    created = 0

    for category_name in DEFAULT_PRODUCT_CATEGORIES:
        if Category.objects.count() >= min_count:
            break
        if category_name.casefold() in existing_names:
            continue
        Category.objects.create(name=category_name)
        existing_names.add(category_name.casefold())
        created += 1

    suffix = 1
    while Category.objects.count() < min_count:
        fallback_name = f"Category {suffix}"
        suffix += 1
        if fallback_name.casefold() in existing_names:
            continue
        Category.objects.create(name=fallback_name)
        existing_names.add(fallback_name.casefold())
        created += 1

    return {
        "created": created,
        "total": Category.objects.count(),
    }