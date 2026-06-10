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

    ELECTRONICS_DEFAULTS = {
        'brand': '',
        'model': '',
        'warranty_months': 12,
        'power': '',
        'origin': '',
    }

    MOBILE_DEFAULTS = {
        'brand': '',
        'storage': '64GB',
        'ram': '4GB',
        'battery': '4000mAh',
        'os': 'Android',
    }

    HOME_APPLIANCE_DEFAULTS = {
        'brand': '',
        'power': '',
        'capacity': '',
        'energy_rating': '',
        'warranty_months': 12,
    }

    BEAUTY_DEFAULTS = {
        'brand': '',
        'skin_type': 'All',
        'volume': '',
        'expiry_date': '',
        'origin': '',
    }

    FOOD_DEFAULTS = {
        'brand': '',
        'weight': '',
        'expiry_date': '',
        'origin': '',
        'flavor': '',
    }

    FURNITURE_DEFAULTS = {
        'material': '',
        'dimensions': '',
        'weight': '',
        'color': '',
        'style': '',
    }

    SPORTS_DEFAULTS = {
        'brand': '',
        'sport_type': '',
        'material': '',
        'size': '',
        'gender_target': 'Unisex',
    }

    TOYS_DEFAULTS = {
        'brand': '',
        'age_range': '3+',
        'material': '',
        'safety_certification': '',
        'educational': False,
    }

    PRODUCT_DETAIL_KEYS = {
        'book': ('book_details', BOOK_DEFAULTS),
        'clothing': ('clothing_details', CLOTHING_DEFAULTS),
        'electronics': ('electronics_details', ELECTRONICS_DEFAULTS),
        'mobile': ('mobile_details', MOBILE_DEFAULTS),
        'home_appliance': ('home_appliance_details', HOME_APPLIANCE_DEFAULTS),
        'beauty': ('beauty_details', BEAUTY_DEFAULTS),
        'food': ('food_details', FOOD_DEFAULTS),
        'furniture': ('furniture_details', FURNITURE_DEFAULTS),
        'sports': ('sports_details', SPORTS_DEFAULTS),
        'toys': ('toys_details', TOYS_DEFAULTS),
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
    def get_details_by_product_type(product_type: str, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Extract details from attributes by product type using default fallbacks."""
        detail_key, defaults = ProductAttributeManager.PRODUCT_DETAIL_KEYS.get(str(product_type), ('', {}))
        if not detail_key:
            return {}
        if isinstance(attributes, dict) and detail_key in attributes and isinstance(attributes[detail_key], dict):
            return {**defaults, **attributes[detail_key]}
        return defaults.copy()

    @staticmethod
    def set_details_by_product_type(product_type: str, attributes: Dict[str, Any], details: Dict[str, Any]) -> Dict[str, Any]:
        """Set details into attributes by product type key."""
        detail_key, _ = ProductAttributeManager.PRODUCT_DETAIL_KEYS.get(str(product_type), ('', {}))
        if not detail_key:
            return attributes if isinstance(attributes, dict) else {}
        if not isinstance(attributes, dict):
            attributes = {}
        attributes[detail_key] = details if isinstance(details, dict) else {}
        return attributes
    
    @staticmethod
    def get_attribute_for_product(product: 'Book', key: str, default: Any = None) -> Any:
        """Get specific attribute value for a product based on its type"""
        details = ProductAttributeManager.get_details_by_product_type(product.product_type, product.attributes)
        if details:
            return details.get(key, default)
        return default


# Export for use in views
__all__ = ['ProductAttributeManager']
