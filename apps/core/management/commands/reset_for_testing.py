"""Management command to reset data for testing: delete non-admin users, clear conversations, and create test users."""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.core.models import Customer
from apps.conversations.models import Conversation


class Command(BaseCommand):
    help = 'Delete non-admin users, clear conversations, and create two test users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Skip confirmation prompt',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(self.style.WARNING(
                '⚠️  This will delete all non-admin users, clear all conversations, and create test users.'
            ))
            confirm = input('Are you sure? Type "yes" to continue: ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Operation cancelled.'))
                return

        # Step 1: Delete all conversations
        self.stdout.write('\n🗑️  Deleting all conversations...')
        conversation_count = Conversation.objects.count()
        Conversation.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'✓ Deleted {conversation_count} conversations'))

        # Step 2: Delete all customers (they will be recreated with new users)
        self.stdout.write('\n🗑️  Deleting all customers...')
        customer_count = Customer.objects.count()
        Customer.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'✓ Deleted {customer_count} customers'))

        # Step 3: Delete non-admin users (keep superusers and staff)
        self.stdout.write('\n🗑️  Deleting non-admin users...')
        non_admin_users = User.objects.filter(is_superuser=False, is_staff=False)
        user_count = non_admin_users.count()
        deleted_users = []
        for user in non_admin_users:
            deleted_users.append(f'{user.username} ({user.get_full_name() or "no name"})')
        non_admin_users.delete()
        self.stdout.write(self.style.SUCCESS(f'✓ Deleted {user_count} non-admin users:'))
        for user_info in deleted_users:
            self.stdout.write(f'   - {user_info}')

        # Step 4: Create two test users
        self.stdout.write('\n👤 Creating test users...')
        
        # Test User 1
        try:
            user1, created1 = User.objects.get_or_create(
                username='testuser1@test.com',
                defaults={
                    'email': 'testuser1@test.com',
                    'first_name': 'Test',
                    'last_name': 'User One',
                    'is_staff': False,
                    'is_superuser': False,
                }
            )
            if not created1:
                user1.first_name = 'Test'
                user1.last_name = 'User One'
                user1.email = 'testuser1@test.com'
                user1.set_password('testpass123')
                user1.save()
            else:
                user1.set_password('testpass123')
                user1.save()
            self.stdout.write(self.style.SUCCESS(
                f'✓ Created/Updated User 1: {user1.username} ({user1.get_full_name()})'
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error creating User 1: {str(e)}'))

        # Test User 2
        try:
            user2, created2 = User.objects.get_or_create(
                username='testuser2@test.com',
                defaults={
                    'email': 'testuser2@test.com',
                    'first_name': 'Test',
                    'last_name': 'User Two',
                    'is_staff': False,
                    'is_superuser': False,
                }
            )
            if not created2:
                user2.first_name = 'Test'
                user2.last_name = 'User Two'
                user2.email = 'testuser2@test.com'
                user2.set_password('testpass123')
                user2.save()
            else:
                user2.set_password('testpass123')
                user2.save()
            self.stdout.write(self.style.SUCCESS(
                f'✓ Created/Updated User 2: {user2.username} ({user2.get_full_name()})'
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error creating User 2: {str(e)}'))

        # Summary
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Reset complete!\n'
            f'\nTest Users Created:'
            f'\n  1. Email: testuser1@test.com, Password: testpass123, Name: Test User One'
            f'\n  2. Email: testuser2@test.com, Password: testpass123, Name: Test User Two'
            f'\n\nYou can now log in with these accounts to test the conversation features.'
        ))
