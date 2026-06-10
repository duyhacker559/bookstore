from django.db import models
from django.db.models import ForeignKey, CASCADE, SET_NULL


class Product(models.Model):
    PRODUCT_TYPE_BOOK = "book"
    PRODUCT_TYPE_CLOTHING = "clothing"
    PRODUCT_TYPE_ELECTRONICS = "electronics"
    PRODUCT_TYPE_MOBILE = "mobile"
    PRODUCT_TYPE_HOME_APPLIANCE = "home_appliance"
    PRODUCT_TYPE_BEAUTY = "beauty"
    PRODUCT_TYPE_FOOD = "food"
    PRODUCT_TYPE_FURNITURE = "furniture"
    PRODUCT_TYPE_SPORTS = "sports"
    PRODUCT_TYPE_TOYS = "toys"
    PRODUCT_TYPE_CHOICES = [
        (PRODUCT_TYPE_BOOK, "Book"),
        (PRODUCT_TYPE_CLOTHING, "Clothing"),
        (PRODUCT_TYPE_ELECTRONICS, "Electronics"),
        (PRODUCT_TYPE_MOBILE, "Mobile"),
        (PRODUCT_TYPE_HOME_APPLIANCE, "Home Appliance"),
        (PRODUCT_TYPE_BEAUTY, "Beauty"),
        (PRODUCT_TYPE_FOOD, "Food"),
        (PRODUCT_TYPE_FURNITURE, "Furniture"),
        (PRODUCT_TYPE_SPORTS, "Sports"),
        (PRODUCT_TYPE_TOYS, "Toys"),
    ]

    title = models.CharField(max_length=255)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES, default=PRODUCT_TYPE_BOOK, db_index=True)
    author = models.CharField(max_length=255, blank=True, default="", help_text="Legacy field - use author_fk instead")
    brand = models.CharField(max_length=255, blank=True, default="")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    category = models.CharField(max_length=100, blank=True, null=True, help_text="Legacy field - use category_fk instead")
    size_options = models.CharField(max_length=100, blank=True, default="", help_text="Comma-separated sizes, e.g. S,M,L,XL")
    material = models.CharField(max_length=120, blank=True, default="")
    gender_target = models.CharField(max_length=32, blank=True, default="")
    
    # New ForeignKey relationships (Microservices Phase 1)
    author_fk = models.ForeignKey('store.Author', on_delete=SET_NULL, null=True, blank=True, related_name='products_by_fk')
    category_fk = models.ForeignKey('store.Category', on_delete=SET_NULL, null=True, blank=True, related_name='products_by_fk')
    categories_m2m = models.ManyToManyField('store.Category', blank=True, related_name='products_multi')
    description = models.TextField(blank=True)
    attributes = models.JSONField(default=dict, blank=True)
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=0.0)  # 0.0 to 5.0
    review_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'store'
        db_table = 'store_product'

    def __str__(self):
        return self.title

    @property
    def category_names(self):
        names = [category.name for category in self.categories_m2m.all() if category.name]
        if names:
            return names

        fallback = []
        if self.category_fk and self.category_fk.name:
            fallback.append(self.category_fk.name)
        if self.category and self.category.strip() and self.category.strip() not in fallback:
            fallback.append(self.category.strip())
        return fallback

    @property
    def primary_category(self):
        names = self.category_names
        return names[0] if names else ""

    @property
    def categories_display(self):
        return ", ".join(self.category_names)

    @property
    def creator_display(self):
        if self.product_type == self.PRODUCT_TYPE_CLOTHING:
            return self.brand or self.author or "Unknown brand"
        return self.author or self.brand or "Unknown author"

    @property
    def creator_label(self):
        return "Brand" if self.product_type == self.PRODUCT_TYPE_CLOTHING else "Author"

    @property
    def size_list(self):
        if not self.size_options:
            return []
        return [size.strip() for size in self.size_options.split(",") if size.strip()]

