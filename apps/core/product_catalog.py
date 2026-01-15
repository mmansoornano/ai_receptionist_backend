"""Product catalog with product information from database."""
from django.core.cache import cache
from .models import Product


def get_product(product_id):
    """Get product information by ID from database."""
    if not product_id:
        return None
    
    # Try cache first
    cache_key = f'product_{product_id}'
    product = cache.get(cache_key)
    
    if product is None:
        try:
            product = Product.objects.get(product_id=product_id, is_active=True)
            # Cache for 1 hour
            cache.set(cache_key, product, 3600)
        except Product.DoesNotExist:
            return None
    
    return {
        'product_id': product.product_id,
        'name': product.name,
        'price': float(product.price),
        'description': product.description,
        'category': product.category
    }


def get_product_name(product_id):
    """Get product name by ID from database."""
    product = get_product(product_id)
    return product['name'] if product else product_id


def get_product_price(product_id):
    """Get product price by ID from database."""
    product = get_product(product_id)
    return product['price'] if product else 0.00


def is_valid_product(product_id):
    """Check if product ID is valid in database."""
    if not product_id:
        return False
    return Product.objects.filter(product_id=product_id, is_active=True).exists()
