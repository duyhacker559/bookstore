"""
Product Category Forms - Dynamic forms for different product categories
"""

from django import forms
from store.models import Book


class BaseProductForm(forms.ModelForm):
    """Base form for product with common fields"""
    class Meta:
        model = Book
        fields = ['title', 'description', 'price', 'stock', 'product_type', 
                  'category_fk', 'categories_m2m', 'rating']


class BookProductForm(BaseProductForm):
    """Form for Book products with book-specific fields"""
    author = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Author name'}),
        label='Author'
    )
    publisher = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Publisher'}),
        label='Publisher'
    )
    pages = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'placeholder': 'Number of pages'}),
        label='Pages'
    )
    language = forms.CharField(
        max_length=50,
        required=False,
        initial='Vietnamese',
        widget=forms.TextInput(attrs={'placeholder': 'Language'}),
        label='Language'
    )
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set product type to book
        instance.product_type = 'book'
        
        # Store book details in attributes
        attributes = instance.attributes or {}
        attributes['book_details'] = {
            'author': self.cleaned_data.get('author', ''),
            'publisher': self.cleaned_data.get('publisher', ''),
            'pages': self.cleaned_data.get('pages', 0),
            'language': self.cleaned_data.get('language', 'Vietnamese'),
        }
        instance.attributes = attributes
        
        if commit:
            instance.save()
        return instance


class ClothingProductForm(BaseProductForm):
    """Form for Clothing products with clothing-specific fields"""
    brand = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Brand name'}),
        label='Brand'
    )
    sizes = forms.CharField(
        max_length=100,
        required=False,
        initial='S,M,L,XL',
        widget=forms.TextInput(attrs={'placeholder': 'Comma-separated sizes (S,M,L,XL)'}),
        label='Available Sizes'
    )
    material = forms.CharField(
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Material (e.g. Cotton, Polyester)'}),
        label='Material'
    )
    gender_target = forms.CharField(
        max_length=32,
        required=False,
        initial='Unisex',
        widget=forms.TextInput(attrs={'placeholder': 'Gender Target (Unisex, Men, Women)'}),
        label='Gender Target'
    )
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set product type to clothing
        instance.product_type = 'clothing'
        
        # Store clothing details in attributes
        attributes = instance.attributes or {}
        attributes['clothing_details'] = {
            'brand': self.cleaned_data.get('brand', ''),
            'sizes': self.cleaned_data.get('sizes', 'S,M,L,XL'),
            'material': self.cleaned_data.get('material', ''),
            'gender_target': self.cleaned_data.get('gender_target', 'Unisex'),
        }
        instance.attributes = attributes
        
        if commit:
            instance.save()
        return instance


def get_product_form_class(product_type: str) -> type:
    """Return appropriate form class based on product type"""
    if product_type == 'book':
        return BookProductForm
    elif product_type == 'clothing':
        return ClothingProductForm
    else:
        return BaseProductForm
