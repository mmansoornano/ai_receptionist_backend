"""Management command to update customer names from linked users."""
from django.core.management.base import BaseCommand
from apps.core.models import Customer
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Update customer names from their linked users'

    def handle(self, *args, **options):
        updated_count = 0
        skipped_count = 0
        
        customers = Customer.objects.all()
        
        for customer in customers:
            # If customer has a linked user, get name from user
            if customer.user:
                user = customer.user
                proper_name = user.get_full_name() or user.first_name or user.username
                
                if proper_name and proper_name.strip():
                    # Update if name is missing, 'Unknown', or different
                    if not customer.name or customer.name == 'Unknown' or customer.name != proper_name:
                        old_name = customer.name or '(empty)'
                        customer.name = proper_name
                        customer.save(update_fields=['name'])
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'✓ Updated Customer {customer.id}: "{old_name}" → "{proper_name}" (User: {user.username})'
                            )
                        )
                        updated_count += 1
                    else:
                        skipped_count += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'⚠ Customer {customer.id} has user {customer.user.username} but user has no name'
                        )
                    )
            else:
                # Try to find user by email
                if customer.email:
                    try:
                        user = User.objects.filter(email=customer.email).first()
                        if user:
                            proper_name = user.get_full_name() or user.first_name or user.username
                            if proper_name and proper_name.strip():
                                # Link user and update name
                                customer.user = user
                                customer.name = proper_name
                                customer.save(update_fields=['user', 'name'])
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f'✓ Linked and updated Customer {customer.id}: "{customer.name}" → "{proper_name}" (User: {user.username})'
                                    )
                                )
                                updated_count += 1
                            else:
                                skipped_count += 1
                        else:
                            skipped_count += 1
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f'✗ Error processing Customer {customer.id}: {str(e)}'
                            )
                        )
                else:
                    skipped_count += 1
        
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Update complete! Updated: {updated_count}, Skipped: {skipped_count}'
        ))
