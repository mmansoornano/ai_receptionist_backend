"""Management command to clear all customer, conversation, order, and related data."""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.core.models import (
    Customer, Appointment, Cart, CartItem, Payment, Order, Cancellation, Product
)
from apps.conversations.models import Conversation


class Command(BaseCommand):
    help = 'Clear all customer data, conversations, orders, payments, carts, and related data from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Skip confirmation prompt',
        )
        parser.add_argument(
            '--keep-products',
            action='store_true',
            help='Keep product catalog data',
        )
        parser.add_argument(
            '--keep-superusers',
            action='store_true',
            help='Keep superuser accounts',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(self.style.WARNING(
                '\n⚠️  WARNING: This will delete ALL data from the database:\n'
                '  - All customers\n'
                '  - All conversations\n'
                '  - All orders\n'
                '  - All payments\n'
                '  - All carts and cart items\n'
                '  - All appointments\n'
                '  - All cancellations\n'
            ))
            if not options['keep_products']:
                self.stdout.write('  - All products\n')
            if not options['keep_superusers']:
                self.stdout.write('  - All users (including admin)\n')
            
            confirm = input('\nType "yes" to continue: ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Operation cancelled.'))
                return

        # Delete in order to respect foreign key constraints
        deleted_counts = {}

        self.stdout.write('\nClearing data...\n')

        # Helper function to safely delete
        def safe_delete(model_class, name):
            try:
                count = model_class.objects.all().delete()[0]
                deleted_counts[name] = count
                self.stdout.write(self.style.SUCCESS(f'✓ Deleted {count} {name.lower()}'))
                return True
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'⚠ Could not delete {name.lower()}: {str(e)}'))
                deleted_counts[name] = 0
                return False

        # 1. Cancellations (depends on Orders)
        safe_delete(Cancellation, 'Cancellations')

        # 2. Payments (depends on Orders)
        safe_delete(Payment, 'Payments')

        # 3. Orders (try raw SQL if model delete fails)
        try:
            count = Order.objects.all().delete()[0]
            deleted_counts['Orders'] = count
            self.stdout.write(self.style.SUCCESS(f'✓ Deleted {count} orders'))
        except Exception as e:
            # Try raw SQL deletion
            try:
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute('DELETE FROM core_order')
                    count = cursor.rowcount
                    deleted_counts['Orders'] = count
                    self.stdout.write(self.style.SUCCESS(f'✓ Deleted {count} orders (using raw SQL)'))
            except Exception as sql_error:
                self.stdout.write(self.style.WARNING(f'⚠ Could not delete orders: {str(e)}'))
                deleted_counts['Orders'] = 0

        # 4. Cart Items (depends on Cart)
        safe_delete(CartItem, 'Cart Items')

        # 5. Carts
        safe_delete(Cart, 'Carts')

        # 6. Conversations (depends on Customer)
        safe_delete(Conversation, 'Conversations')

        # 7. Appointments (depends on Customer)
        safe_delete(Appointment, 'Appointments')

        # 8. Customers
        safe_delete(Customer, 'Customers')

        # 9. Products (optional)
        if not options['keep_products']:
            count = Product.objects.all().delete()[0]
            deleted_counts['Products'] = count
            self.stdout.write(self.style.SUCCESS(f'✓ Deleted {count} products'))
        else:
            self.stdout.write(self.style.WARNING('⚠ Skipped products (--keep-products)'))

        # 10. Users (optional - keep superusers)
        if not options['keep_superusers']:
            count = User.objects.all().delete()[0]
            deleted_counts['Users'] = count
            self.stdout.write(self.style.SUCCESS(f'✓ Deleted {count} users'))
        else:
            # Delete only non-superuser accounts
            count = User.objects.filter(is_superuser=False).delete()[0]
            deleted_counts['Regular Users'] = count
            self.stdout.write(self.style.SUCCESS(f'✓ Deleted {count} regular users'))
            self.stdout.write(self.style.WARNING('⚠ Kept superuser accounts'))

        # Summary
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Successfully cleared all data!\n'
            f'\nSummary:'
        ))
        for model_name, count in deleted_counts.items():
            self.stdout.write(f'  {model_name}: {count}')

        self.stdout.write(self.style.SUCCESS('\n✨ Database is now clean and ready for fresh data!'))
