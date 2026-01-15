"""Management command to populate products from the original catalog."""
from django.core.management.base import BaseCommand
from apps.core.models import Product


# Original product catalog data
PRODUCT_DATA = [
    {'product_id': 'protein-bar-white-chocolate', 'name': 'White Chocolate Brownie Protein Bar', 'price': 450.00, 'category': 'protein-bar'},
    {'product_id': 'protein-bar-almond', 'name': 'Almond Brownie Protein Bar', 'price': 450.00, 'category': 'protein-bar'},
    {'product_id': 'protein-bar-peanut-butter', 'name': 'Peanut Butter Fudge Protein Bar', 'price': 450.00, 'category': 'protein-bar'},
    {'product_id': 'protein-mini', 'name': 'Chewy Protein Mini', 'price': 200.00, 'category': 'protein-mini'},
    {'product_id': 'granola-bar-chocolate-walnut', 'name': 'Chocolate & Walnut Granola Bar', 'price': 220.00, 'category': 'granola-bar'},
    {'product_id': 'granola-bar-chocolate-pb', 'name': 'Chocolate & Peanut Butter Granola Bar', 'price': 220.00, 'category': 'granola-bar'},
    {'product_id': 'granola-bar-coffee-pumpkin', 'name': 'Coffee & Pumpkin Seed Granola Bar', 'price': 220.00, 'category': 'granola-bar'},
    {'product_id': 'granola-bar-crunchy', 'name': 'Crunchy Choco Grain Granola Bar', 'price': 220.00, 'category': 'granola-bar'},
    {'product_id': 'granola-cereal-chocolate', 'name': 'Chocolate, Fruit & Nut Granola Cereal', 'price': 800.00, 'category': 'granola-cereal'},
    {'product_id': 'granola-cereal-pbj', 'name': 'Peanut Butter & Jelly Granola Cereal', 'price': 800.00, 'category': 'granola-cereal'},
    {'product_id': 'cookie-chocolate', 'name': 'Chocolate Chunks Cookie', 'price': 200.00, 'category': 'cookie'},
    {'product_id': 'cookie-pb', 'name': 'Peanut Butter Cookie', 'price': 200.00, 'category': 'cookie'},
    {'product_id': 'gift-box-all-bars', 'name': 'Gift Box - All Bars', 'price': 3580.00, 'category': 'gift-box'},
    {'product_id': 'gift-box-all-bars-cereal', 'name': 'Gift Box – All Bars & Granola Cereals', 'price': 4320.00, 'category': 'gift-box'},
]


class Command(BaseCommand):
    help = 'Populate products from the original catalog'

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0
        
        for product_data in PRODUCT_DATA:
            product, created = Product.objects.update_or_create(
                product_id=product_data['product_id'],
                defaults={
                    'name': product_data['name'],
                    'price': product_data['price'],
                    'category': product_data['category'],
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created product: {product.name}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated product: {product.name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully processed {len(PRODUCT_DATA)} products: '
                f'{created_count} created, {updated_count} updated'
            )
        )
