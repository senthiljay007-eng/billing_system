from django.contrib import admin

from .models import Denomination, Invoice, InvoiceItem, Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_id', 'name', 'available_stocks', 'price_per_unit', 'tax_percentage')
    search_fields = ('product_id', 'name')


@admin.register(Denomination)
class DenominationAdmin(admin.ModelAdmin):
    list_display = ('value', 'available_count')
    ordering = ('-value',)


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0
    readonly_fields = (
        'product', 'product_name', 'unit_price', 'tax_percentage',
        'quantity', 'purchase_price', 'tax_payable', 'total_price',
    )
    can_delete = False


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_email', 'created_at', 'rounded_net_price', 'balance_amount', 'email_sent')
    search_fields = ('customer_email',)
    list_filter = ('email_sent', 'created_at')
    inlines = [InvoiceItemInline]
    readonly_fields = [f.name for f in Invoice._meta.fields]

    def has_add_permission(self, request):
        return False
