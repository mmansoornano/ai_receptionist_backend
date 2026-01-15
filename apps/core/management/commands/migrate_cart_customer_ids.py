"""Migrate cart.customer_id from Customer.id to User.id for webchat users."""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.core.models import Cart, CartItem, Customer


class Command(BaseCommand):
    help = "Migrate cart.customer_id values to use User.id (webchat canonical ID)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show changes without applying them",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        updated = 0
        merged = 0
        skipped = 0

        customers = Customer.objects.exclude(user__isnull=True).select_related("user")
        customer_map = {str(c.id): str(c.user.id) for c in customers}

        carts = Cart.objects.all().prefetch_related("items")
        for cart in carts:
            raw_id = cart.customer_id or ""
            customer_id = raw_id.replace("customer_", "")
            target_id = customer_map.get(customer_id)

            if not target_id:
                skipped += 1
                continue

            if target_id == cart.customer_id:
                skipped += 1
                continue

            # Merge into existing target cart if present
            target_cart = Cart.objects.filter(customer_id=target_id).first()

            if dry_run:
                action = "merge" if target_cart else "update"
                self.stdout.write(f"[DRY RUN] {action} cart {cart.id} -> {target_id}")
                continue

            with transaction.atomic():
                if target_cart:
                    for item in cart.items.all():
                        existing = CartItem.objects.filter(
                            cart=target_cart,
                            product_id=item.product_id
                        ).first()
                        if existing:
                            existing.quantity += item.quantity
                            existing.save(update_fields=["quantity"])
                            item.delete()
                        else:
                            item.cart = target_cart
                            item.save(update_fields=["cart"])
                    cart.delete()
                    merged += 1
                else:
                    cart.customer_id = target_id
                    cart.save(update_fields=["customer_id"])
                    updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Cart migration complete. Updated: {updated}, Merged: {merged}, Skipped: {skipped}"
        ))
