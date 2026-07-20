from django.core.management.base import BaseCommand

from billing.models import Denomination, Product

DEFAULT_PRODUCTS = [
    {'product_id': 'P001', 'name': 'Wireless Mouse', 'available_stocks': 50, 'price_per_unit': 499.00, 'tax_percentage': 18},
    {'product_id': 'P002', 'name': 'Mechanical Keyboard', 'available_stocks': 30, 'price_per_unit': 1899.00, 'tax_percentage': 18},
    {'product_id': 'P003', 'name': 'USB-C Cable', 'available_stocks': 100, 'price_per_unit': 149.00, 'tax_percentage': 12},
    {'product_id': 'P004', 'name': '20000mAh Power Bank', 'available_stocks': 40, 'price_per_unit': 1299.00, 'tax_percentage': 18},
    {'product_id': 'P005', 'name': 'Notebook (200 pages)', 'available_stocks': 200, 'price_per_unit': 45.00, 'tax_percentage': 5},
]

DEFAULT_DENOMINATIONS = [
    {'value': 500, 'available_count': 10},
    {'value': 50, 'available_count': 20},
    {'value': 20, 'available_count': 15},
    {'value': 10, 'available_count': 15},
    {'value': 5, 'available_count': 10},
    {'value': 2, 'available_count': 10},
    {'value': 1, 'available_count': 10},
]


class Command(BaseCommand):
    help = "Seeds the database with sample products and default shop denominations."

    def handle(self, *args, **options):
        created_products = 0
        for data in DEFAULT_PRODUCTS:
            _, created = Product.objects.get_or_create(product_id=data['product_id'], defaults=data)
            created_products += created

        created_denoms = 0
        for data in DEFAULT_DENOMINATIONS:
            _, created = Denomination.objects.get_or_create(value=data['value'], defaults=data)
            created_denoms += created

        self.stdout.write(self.style.SUCCESS(
            f"Seed complete: {created_products} product(s) and {created_denoms} denomination(s) created."
        ))
