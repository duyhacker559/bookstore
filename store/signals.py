import logging
import os

from django.db.models.signals import post_migrate
from django.dispatch import receiver

from store.services.category_seed import ensure_minimum_product_categories

logger = logging.getLogger(__name__)


@receiver(post_migrate)
def seed_minimum_categories(sender, **kwargs):
    if sender.name != "store":
        return
    if os.environ.get("STORE_SKIP_CATEGORY_AUTOSEED", "0") == "1":
        return

    result = ensure_minimum_product_categories(min_count=10)
    if result["created"] > 0:
        logger.info(
            "Seeded product categories after migrate: created=%s total=%s",
            result["created"],
            result["total"],
        )
