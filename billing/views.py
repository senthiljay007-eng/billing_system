from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .emails import send_invoice_email_async
from .forms import BillingInfoForm, BillItemFormSet, DenominationForm
from .models import Invoice, Product
from .services import InsufficientPaymentError, generate_bill


def bill_create_view(request):
    if request.method == 'POST':
        info_form = BillingInfoForm(request.POST)
        item_formset = BillItemFormSet(request.POST, prefix='items')
        denom_form = DenominationForm(request.POST)

        if info_form.is_valid() and item_formset.is_valid() and denom_form.is_valid():
            item_rows = [
                {'product': form.cleaned_data['product'], 'quantity': form.cleaned_data['quantity']}
                for form in item_formset
                if form.cleaned_data and not form.cleaned_data.get('DELETE')
            ]

            if not item_rows:
                messages.error(request, "Please add at least one product to the bill.")
            else:
                try:
                    invoice = generate_bill(
                        customer_email=info_form.cleaned_data['customer_email'],
                        cash_paid=info_form.cleaned_data['cash_paid'],
                        item_rows=item_rows,
                        denomination_counts=denom_form.get_counts(),
                    )
                    send_invoice_email_async(invoice.pk)
                    return redirect('billing:invoice_detail', invoice_id=invoice.pk)
                except InsufficientPaymentError as exc:
                    messages.error(request, str(exc))
    else:
        info_form = BillingInfoForm()
        item_formset = BillItemFormSet(prefix='items')
        denom_form = DenominationForm()

    return render(request, 'billing/bill_form.html', {
        'info_form': info_form,
        'item_formset': item_formset,
        'denom_form': denom_form,
    })


def invoice_detail_view(request, invoice_id):
    invoice = get_object_or_404(Invoice.objects.prefetch_related('items'), pk=invoice_id)
    breakdown = sorted(
        ((int(value), count) for value, count in invoice.balance_denomination_breakdown.items()),
        reverse=True,
    )
    return render(request, 'billing/invoice_detail.html', {
        'invoice': invoice,
        'breakdown': breakdown,
    })


def product_lookup_view(request):
    """Looks up a product by its Product ID for the live name-preview on
    Page 1 (see the JS in bill_form.html). Read-only, no side effects, so a
    plain GET is fine here."""
    product_id = request.GET.get('product_id', '').strip()
    try:
        product = Product.objects.get(product_id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({'found': False})

    return JsonResponse({
        'found': True,
        'name': product.name,
        'available_stocks': product.available_stocks,
    })


def customer_purchases_view(request):
    email = request.GET.get('email', '').strip()
    invoices = None
    if email:
        invoices = Invoice.objects.filter(customer_email__iexact=email)
    return render(request, 'billing/customer_purchases.html', {
        'email': email,
        'invoices': invoices,
    })
