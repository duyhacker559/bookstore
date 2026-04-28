# Product Category Architecture - Category-Specific Attributes

## Overview
Refactored from `store_book` (mixed book+clothing) to `store_product` with **category-specific attributes** using JSONField.

## Database Structure

### Core Table: `store_product`
```
- id (PK)
- title (CharField)
- description (TextField)
- product_type (CharField: 'book' or 'clothing')
- category_fk (ForeignKey to Category) - main category
- categories_m2m (ManyToMany to Category) - multiple categories
- price (DecimalField)
- stock (PositiveIntegerField)
- rating (DecimalField)
- review_count (PositiveIntegerField)
- attributes (JSONField) ← **NEW: stores category-specific data**
- created_at, updated_at (DateTime)

[Deprecated fields kept for backward compatibility]
- author (CharField)
- brand (CharField)
- size_options (CharField)
- material (CharField)
- gender_target (CharField)
```

### Attributes Structure (JSONField)

**For Books:**
```json
{
  "book_details": {
    "author": "Author Name",
    "publisher": "Publisher Name",
    "pages": 320,
    "language": "Vietnamese"
  }
}
```

**For Clothing:**
```json
{
  "clothing_details": {
    "brand": "Nike",
    "sizes": "S,M,L,XL",
    "material": "Cotton",
    "gender_target": "Unisex"
  }
}
```

## Installation & Setup

### Step 1: Run Migrations
```bash
python manage.py migrate
```

This will:
- Add `attributes` JSONField to Book model
- Mark old fields as deprecated

### Step 2: Migrate Existing Data
```bash
python manage.py migrate_product_attributes
```

This will:
- Read existing book/clothing fields
- Populate `attributes[book_details]` or `attributes[clothing_details]`
- Preserve all data

## Usage Guide

### 1. Add Products (Admin/API)

#### Using Forms (Django Views)
```python
from store.forms.product_forms import get_product_form_class

# For Books
BookForm = get_product_form_class('book')
form = BookForm(data=request.POST)

# For Clothing
ClothingForm = get_product_form_class('clothing')
form = ClothingForm(data=request.POST)

if form.is_valid():
    product = form.save()
    # attributes automatically populated
```

#### Using Manager (Programmatic)
```python
from store.models import Book
from store.models.product.attribute_manager import ProductAttributeManager

# Create book
book = Book.objects.create(
    title="Python Guide",
    product_type='book',
    price=250000,
    stock=50
)

# Set book attributes
attributes = ProductAttributeManager.set_book_details(book.attributes or {}, {
    'author': 'John Doe',
    'publisher': 'Tech Press',
    'pages': 320,
    'language': 'English'
})
book.attributes = attributes
book.save()
```

### 2. Render UI (Dynamic Based on Category)

#### In Templates
```django
{% if product.product_type == 'book' %}
  <div class="book-details">
    <p>Author: {{ product.attributes.book_details.author }}</p>
    <p>Pages: {{ product.attributes.book_details.pages }}</p>
    <p>Language: {{ product.attributes.book_details.language }}</p>
  </div>
{% elif product.product_type == 'clothing' %}
  <div class="clothing-details">
    <p>Brand: {{ product.attributes.clothing_details.brand }}</p>
    <p>Available Sizes: {{ product.attributes.clothing_details.sizes }}</p>
    <p>Material: {{ product.attributes.clothing_details.material }}</p>
    <p>Gender: {{ product.attributes.clothing_details.gender_target }}</p>
  </div>
{% endif %}
```

#### In Python Views
```python
from store.models.product.attribute_manager import ProductAttributeManager

product = Book.objects.get(id=1)

if product.product_type == 'book':
    book_details = ProductAttributeManager.get_book_details(product.attributes)
    author = book_details['author']
    pages = book_details['pages']
else:
    clothing_details = ProductAttributeManager.get_clothing_details(product.attributes)
    brand = clothing_details['brand']
    sizes = clothing_details['sizes']
```

### 3. Search & Filter

#### Basic Search
```python
from store.services.product_search import ProductSearchFilter
from store.models import Book

# Search books by title/author/description
books = ProductSearchFilter.filter_by_category(Book.objects.all(), 'book')
results = ProductSearchFilter.search(books, 'python', product_type='book')
```

#### Advanced Filters
```python
# Filter by author
results = ProductSearchFilter.filter_books_by_author(books, 'John Doe')

# Filter by brand
clothing = ProductSearchFilter.filter_by_category(Book.objects.all(), 'clothing')
results = ProductSearchFilter.filter_clothing_by_brand(clothing, 'Nike')

# Filter by size
results = ProductSearchFilter.filter_clothing_by_size(results, 'M')

# Price range
results = ProductSearchFilter.filter_by_price_range(results, min_price=100, max_price=500)

# In stock only
results = ProductSearchFilter.filter_by_stock(results, in_stock_only=True)
```

### 4. Admin Panel (Dynamic Forms)

The staff views should be updated to use category-specific forms:

```python
# store/controllers/staffController/views.py

from store.forms.product_forms import get_product_form_class

def staff_add_product(request):
    product_type = request.POST.get('product_type', 'book')
    FormClass = get_product_form_class(product_type)
    
    if request.method == 'POST':
        form = FormClass(data=request.POST)
        if form.is_valid():
            product = form.save()
            messages.success(request, f"Product '{product.title}' added")
            return redirect('staff_products')
    else:
        form = FormClass()
    
    return render(request, 'staff/product_form.html', {
        'form': form,
        'product_type': product_type
    })
```

## API Examples

### Create Book Product
```bash
POST /api/products/
{
  "title": "Advanced Python",
  "product_type": "book",
  "category_id": 1,
  "price": 350000,
  "stock": 100,
  "attributes": {
    "book_details": {
      "author": "Guido van Rossum",
      "publisher": "O'Reilly",
      "pages": 512,
      "language": "English"
    }
  }
}
```

### Create Clothing Product
```bash
POST /api/products/
{
  "title": "Designer T-Shirt",
  "product_type": "clothing",
  "category_id": 5,
  "price": 150000,
  "stock": 250,
  "attributes": {
    "clothing_details": {
      "brand": "Nike",
      "sizes": "XS,S,M,L,XL,XXL",
      "material": "100% Cotton",
      "gender_target": "Unisex"
    }
  }
}
```

### Search Endpoint
```bash
GET /api/products/search/?category=book&author=John+Doe
GET /api/products/search/?category=clothing&brand=Nike&size=M
GET /api/products/search/?query=python&category=book&price_min=100&price_max=500
```

## Migration Path

### Phase 1: ✓ Database Schema
- [x] Add `attributes` JSONField
- [x] Create migration file
- [x] Mark old fields as deprecated

### Phase 2: Data Migration
- [x] Create migration command: `python manage.py migrate_product_attributes`
- [ ] Run in production
- [ ] Verify all data transferred

### Phase 3: Application Updates
- [ ] Update staff views to use new forms
- [ ] Update product display templates
- [ ] Update search/filter views
- [ ] Update API serializers

### Phase 4: Cleanup (After verification)
- [ ] Remove deprecated fields from database
- [ ] Remove old field references from views/templates

## Benefits

1. **Clean Separation**: Book and clothing attributes are isolated
2. **Flexible**: Easy to add new product categories without database schema changes
3. **Scalable**: JSONField allows arbitrary attributes per category
4. **Backward Compatible**: Old fields kept during transition
5. **Better UX**: Forms and UI render only relevant fields

## Support

- Manager: `ProductAttributeManager`
- Forms: `store.forms.product_forms`
- Search: `store.services.product_search`
- Migration: `python manage.py migrate_product_attributes`

---
**Created:** April 28, 2026
**Status:** Migration Phase 1 Complete
