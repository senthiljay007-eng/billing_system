import logging
import threading

from django.conf import settings
from django.core.mail import send_mail
from django.db import connections
from django.template.loader import render_to_string

from .models import Invoice

logger = logging.getLogger(__name__)


def _send_invoice_email(invoice_id):
    try:
        invoice = Invoice.objects.prefetch_related('items').get(pk=invoice_id)
        body = render_to_string('billing/invoice_email.txt', {'invoice': invoice})
        send_mail(
            subject=f"Your invoice #{invoice.pk}",
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[invoice.customer_email],
        )
        invoice.email_sent = True
        invoice.save(update_fields=['email_sent'])
    except Exception:
        logger.exception("Failed to send invoice email for invoice %s", invoice_id)
    finally:
        # This function runs on its own thread, so it has its own DB
        # connection separate from the request thread's. Django only closes
        # connections automatically at the end of a request, so without this
        # each background thread would leak one open connection permanently.
        connections.close_all()


def send_invoice_email_async(invoice_id):
    """Fires the email send on a background thread so the request/response
    cycle isn't blocked. Simple and dependency-free; swap for Celery if this
    project ever needs a real task queue."""
    thread = threading.Thread(target=_send_invoice_email, args=(invoice_id,), daemon=True)
    thread.start()
