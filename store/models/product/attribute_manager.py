"""
Product Attributes Helper - Manages category-specific product attributes
Supports: Book (author, publisher, pages, language)
          Clothing (brand, size_options, material, gender_target)
"""

from typing import Dict, Any, Optional


class ProductAttributeManager:
    """Manages product attributes based on category/product type"""
    
    BOOK_DEFAULTS = {
        'author': '',
        'publisher': '',
        'pages': 0,
        'language': 'Vietnamese',
    }
    
    CLOTHING_DEFAULTS = {
        'brand': '',
        'sizes': 'S,M,L,XL',  # comma-separated
        'material': '',
        'gender_target': 'Unisex',
    }
    
    @staticmethod
    def get_book_details(attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Extract book-specific details from attributes"""
        if isinstance(attributes, dict) and 'book_details' in attributes:
            return {**ProductAttributeManager.BOOK_DEFAULTS, **attributes['book_details']}
        return ProductAttributeManager.BOOK_DEFAULTS.copy()
    
    @staticmethod
    def get_clothing_details(attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Extract clothing-specific details from attributes"""
        if isinstance(attributes, dict) and 'clothing_details' in attributes:
            return {**ProductAttributeManager.CLOTHING_DEFAULTS, **attributes['clothing_details']}
        return ProductAttributeManager.CLOTHING_DEFAULTS.copy()
    
    @staticmethod
    def set_book_details(attributes: Dict[str, Any], details: Dict[str, Any]) -> Dict[str, Any]:
        """Set book-specific details in attributes"""
        if not isinstance(attributes, dict):
            attributes = {}
        attributes['book_details'] = details
        return attributes
    
    @staticmethod
    def set_clothing_details(attributes: Dict[str, Any], details: Dict[str, Any]) -> Dict[str, Any]:
        """Set clothing-specific details in attributes"""
        if not isinstance(attributes, dict):
            attributes = {}
        attributes['clothing_details'] = details
        return attributes
    
    @staticmethod
    def get_attribute_for_product(product: 'Book', key: str, default: Any = None) -> Any:
        """Get specific attribute value for a product based on its type"""
        if product.product_type == 'book':
            details = ProductAttributeManager.get_book_details(product.attributes)
            return details.get(key, default)
        elif product.product_type == 'clothing':
            details = ProductAttributeManager.get_clothing_details(product.attributes)
            return details.get(key, default)
        return default


# Export for use in views
__all__ = ['ProductAttributeManager']
