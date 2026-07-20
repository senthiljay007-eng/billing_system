import math

from django.db import transaction

from .models import Denomination, Invoice, InvoiceItem


class InsufficientPaymentError(Exception):
    pass


def compute_change_breakdown(balance_amount, available_counts):
    """Greedy change-making bound by what's actually available.

    available_counts: {denomination_value: count}. Mutated counts are not
    reflected here - caller is responsible for persisting stock updates.
    Returns (breakdown: {value: count_used}, unresolved_amount: int).
    """
    remainder = int(round(balance_amount))
    breakdown = {}
    for value in sorted(available_counts.keys(), reverse=True):
        if remainder <= 0:
            break
        count_available = available_counts[value]
        notes_needed = remainder // value
        notes_used = min(notes_needed, count_available)
        if notes_used > 0:
            breakdown[value] = notes_used
            remainder -= notes_used * value
    return breakdown, remainder


@transaction.atomic
def generate_bill(customer_email, cash_paid, item_rows, denomination_counts):
    """item_rows: list of {'product': Product, 'quantity': int}
    denomination_counts: {denomination_value: count} submitted on the form,
    representing the shop's current till counts.

    Returns the created Invoice.
    """
    invoice_items_data = []
    total_before_tax = 0.0
    total_tax_payable = 0.0

    for row in item_rows:
        product = row['product']
        quantity = row['quantity']

        purchase_price = product.price_per_unit * quantity
        tax_payable = purchase_price * product.tax_percentage / 100
        total_price = purchase_price + tax_payable

        total_before_tax += purchase_price
        total_tax_payable += tax_payable

        invoice_items_data.append({
            'product': product,
            'product_name': product.name,
            'unit_price': product.price_per_unit,
            'tax_percentage': product.tax_percentage,
            'quantity': quantity,
            'purchase_price': purchase_price,
            'tax_payable': tax_payable,
            'total_price': total_price,
        })

        product.available_stocks -= quantity
        product.save(update_fields=['available_stocks'])

    net_price = total_before_tax + total_tax_payable
    rounded_net_price = math.floor(net_price)
    balance_amount = round(cash_paid - rounded_net_price, 2)

    if balance_amount < 0:
        raise InsufficientPaymentError(
            f"Cash paid ({cash_paid}) is less than the bill amount ({rounded_net_price})."
        )

    breakdown, unresolved = compute_change_breakdown(balance_amount, denomination_counts)

    invoice = Invoice.objects.create(
        customer_email=customer_email,
        cash_paid=cash_paid,
        total_before_tax=round(total_before_tax, 2),
        total_tax_payable=round(total_tax_payable, 2),
        net_price=round(net_price, 2),
        rounded_net_price=rounded_net_price,
        balance_amount=balance_amount,
        balance_denomination_breakdown={str(k): v for k, v in breakdown.items()},
        unresolved_balance=unresolved,
    )

    for data in invoice_items_data:
        InvoiceItem.objects.create(
            invoice=invoice,
            product=data['product'],
            product_name=data['product_name'],
            unit_price=data['unit_price'],
            tax_percentage=data['tax_percentage'],
            quantity=data['quantity'],
            purchase_price=round(data['purchase_price'], 2),
            tax_payable=round(data['tax_payable'], 2),
            total_price=round(data['total_price'], 2),
        )

    # The notes handed back as change leave the till; persist the cashier's
    # freshly-entered counts minus whatever was just given out.
    denom_lookup = {d.value: d for d in Denomination.objects.select_for_update()}
    for value, count in denomination_counts.items():
        denom = denom_lookup.get(value)
        if denom is None:
            continue
        given = breakdown.get(value, 0)
        denom.available_count = max(count - given, 0)
        denom.save(update_fields=['available_count'])

    return invoice
