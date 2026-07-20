from django import forms
from django.forms import formset_factory

from .models import Denomination, Product


class BillingInfoForm(forms.Form):
    customer_email = forms.EmailField(label='Customer Email')
    cash_paid = forms.FloatField(label='Cash paid by customer', min_value=0.01)


class BillItemForm(forms.Form):
    product_id = forms.CharField(label='Product ID', max_length=20)
    quantity = forms.IntegerField(label='Quantity', min_value=1)

    def clean(self):
        cleaned_data = super().clean()
        product_id = cleaned_data.get('product_id')
        quantity = cleaned_data.get('quantity')
        if not product_id:
            return cleaned_data

        try:
            product = Product.objects.get(product_id=product_id)
        except Product.DoesNotExist:
            raise forms.ValidationError(f"No product found with Product ID '{product_id}'.")

        if quantity is not None and quantity > product.available_stocks:
            raise forms.ValidationError(
                f"Only {product.available_stocks} unit(s) of '{product.name}' are in stock."
            )

        cleaned_data['product'] = product
        return cleaned_data


BillItemFormSet = formset_factory(BillItemForm, extra=1, can_delete=True)


class DenominationForm(forms.Form):
    """Dynamically built with one integer field per Denomination value,
    named `count_<value>`, pre-filled with the shop's current stock."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for denom in Denomination.objects.all():
            self.fields[f'count_{denom.value}'] = forms.IntegerField(
                label=str(denom.value),
                min_value=0,
                initial=denom.available_count,
                required=True,
            )

    def get_counts(self):
        """Returns {denomination_value: count} from cleaned_data."""
        counts = {}
        for field_name, value in self.cleaned_data.items():
            if field_name.startswith('count_'):
                denom_value = int(field_name.replace('count_', ''))
                counts[denom_value] = value
        return counts
