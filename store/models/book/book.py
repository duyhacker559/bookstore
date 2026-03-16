from django.db import models
from django.db.models import ForeignKey, CASCADE, SET_NULL


class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255, help_text="Legacy field - use author_fk instead")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    category = models.CharField(max_length=100, blank=True, null=True, help_text="Legacy field - use category_fk instead")
    
    # New ForeignKey relationships (Microservices Phase 1)
    author_fk = models.ForeignKey('store.Author', on_delete=SET_NULL, null=True, blank=True, related_name='books_by_fk')
    category_fk = models.ForeignKey('store.Category', on_delete=SET_NULL, null=True, blank=True, related_name='books_by_fk')
    categories_m2m = models.ManyToManyField('store.Category', blank=True, related_name='books_multi')
    description = models.TextField(blank=True)
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=0.0)  # 0.0 to 5.0
    review_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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

    class Meta:
        app_label = 'store'
