from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from .models import Denomination, Invoice, Product
from .services import InsufficientPaymentError, compute_change_breakdown, generate_bill


class ComputeChangeBreakdownTests(TestCase):
    """Unit tests for the pure change-making function in services.py."""

    def test_uses_largest_denominations_first(self):
        available = {500: 10, 50: 20, 20: 15, 10: 15, 5: 10, 2: 10, 1: 10}
        breakdown, unresolved = compute_change_breakdown(643, available)
        self.assertEqual(breakdown, {500: 1, 50: 2, 20: 2, 2: 1, 1: 1})
        self.assertEqual(unresolved, 0)

    def test_zero_balance_returns_empty_breakdown(self):
        breakdown, unresolved = compute_change_breakdown(0, {500: 10})
        self.assertEqual(breakdown, {})
        self.assertEqual(unresolved, 0)

    def test_reports_unresolved_amount_when_stock_is_insufficient(self):
        # Only a single 20-note is available, so 45 in change can only
        # partially be made up: one 20-note, 5 left unresolved.
        breakdown, unresolved = compute_change_breakdown(45, {20: 1})
        self.assertEqual(breakdown, {20: 1})
        self.assertEqual(unresolved, 25)


class GenerateBillTests(TestCase):
    """Integration tests for the end-to-end billing calculation in services.py."""

    def setUp(self):
        self.product = Product.objects.create(
            product_id='P001', name='Test Widget', available_stocks=10,
            price_per_unit=100.0, tax_percentage=18,
        )
        for value, count in [(500, 10), (50, 20), (20, 15), (10, 15), (5, 10), (2, 10), (1, 10)]:
            Denomination.objects.create(value=value, available_count=count)

    def test_generate_bill_computes_totals_and_reduces_stock(self):
        invoice = generate_bill(
            customer_email='customer@example.com',
            cash_paid=150,
            item_rows=[{'product': self.product, 'quantity': 1}],
            denomination_counts={500: 10, 50: 20, 20: 15, 10: 15, 5: 10, 2: 10, 1: 10},
        )

        self.assertEqual(invoice.total_before_tax, 100.0)
        self.assertEqual(invoice.total_tax_payable, 18.0)
        self.assertEqual(invoice.net_price, 118.0)
        self.assertEqual(invoice.rounded_net_price, 118)
        self.assertEqual(invoice.balance_amount, 32)
        self.assertEqual(invoice.items.count(), 1)

        self.product.refresh_from_db()
        self.assertEqual(self.product.available_stocks, 9)

    def test_insufficient_cash_raises_and_does_not_create_invoice(self):
        with self.assertRaises(InsufficientPaymentError):
            generate_bill(
                customer_email='customer@example.com',
                cash_paid=50,
                item_rows=[{'product': self.product, 'quantity': 1}],
                denomination_counts={500: 10},
            )
        self.assertEqual(Invoice.objects.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.available_stocks, 10)  # unchanged, transaction rolled back


class BillingViewsTests(TransactionTestCase):
    """Smoke tests for the three pages described in the spec.

    Uses TransactionTestCase (real commits) rather than TestCase (rolled-
    back transactions) because generating a bill spawns a background thread
    with its own DB connection to send the invoice email - a plain TestCase
    would roll back before that thread could ever see the new invoice."""

    def setUp(self):
        self.client = Client()
        self.product = Product.objects.create(
            product_id='P001', name='Test Widget', available_stocks=10,
            price_per_unit=100.0, tax_percentage=18,
        )
        Denomination.objects.create(value=50, available_count=20)
        Denomination.objects.create(value=10, available_count=20)

    def test_bill_form_page_loads(self):
        response = self.client.get(reverse('billing:bill_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Billing Page')

    def test_generate_bill_redirects_to_invoice_detail(self):
        response = self.client.post(reverse('billing:bill_create'), {
            'customer_email': 'customer@example.com',
            'cash_paid': '150',
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-product_id': 'P001',
            'items-0-quantity': '1',
            'count_50': '20',
            'count_10': '20',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Invoice.objects.count(), 1)

        invoice = Invoice.objects.first()
        detail_response = self.client.get(reverse('billing:invoice_detail', args=[invoice.pk]))
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, 'customer@example.com')

    def test_product_lookup_returns_name_for_known_product_id(self):
        response = self.client.get(reverse('billing:product_lookup'), {'product_id': 'P001'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'found': True, 'name': 'Test Widget', 'available_stocks': 10})

    def test_product_lookup_reports_not_found_for_unknown_product_id(self):
        response = self.client.get(reverse('billing:product_lookup'), {'product_id': 'NOPE'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'found': False})

    def test_customer_purchases_lists_matching_invoices(self):
        generate_bill(
            customer_email='customer@example.com',
            cash_paid=150,
            item_rows=[{'product': self.product, 'quantity': 1}],
            denomination_counts={50: 20, 10: 20},
        )
        response = self.client.get(reverse('billing:customer_purchases'), {'email': 'customer@example.com'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'customer@example.com')
