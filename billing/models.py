from django.core.validators import MinValueValidator
from django.db import models


class Product(models.Model):
    product_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)
    available_stocks = models.PositiveIntegerField(default=0)
    price_per_unit = models.FloatField(validators=[MinValueValidator(0)])
    tax_percentage = models.FloatField(validators=[MinValueValidator(0)])

    class Meta:
        ordering = ['product_id']

    def __str__(self):
        return f"{self.product_id} - {self.name}"


class Denomination(models.Model):
    value = models.PositiveIntegerField(unique=True)
    available_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-value']

    def __str__(self):
        return f"{self.value} x {self.available_count}"


class Invoice(models.Model):
    customer_email = models.EmailField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    cash_paid = models.FloatField()
    total_before_tax = models.FloatField()
    total_tax_payable = models.FloatField()
    net_price = models.FloatField()
    rounded_net_price = models.FloatField()
    balance_amount = models.FloatField()

    # {"500": 1, "50": 2, ...} - notes handed back to the customer as change
    balance_denomination_breakdown = models.JSONField(default=dict)
    # Amount of change that couldn't be made with the shop's current
    # denomination stock (should normally be 0). See README assumptions.
    unresolved_balance = models.FloatField(default=0)

    email_sent = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Invoice #{self.pk} - {self.customer_email}"


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='invoice_items', on_delete=models.PROTECT)

    # Snapshots taken at sale time so historical invoices stay accurate even
    # if the product's name/price/tax changes afterwards.
    product_name = models.CharField(max_length=255)
    unit_price = models.FloatField()
    tax_percentage = models.FloatField()
    quantity = models.PositiveIntegerField()

    purchase_price = models.FloatField()
    tax_payable = models.FloatField()
    total_price = models.FloatField()

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"
