from .models import Invoice
from .utils import generate_invoice_number


class InvoiceService:

    @staticmethod
    def create_invoice(order):

        invoice, created = Invoice.objects.get_or_create(
            order=order,
            defaults={
                "invoice_number":
                    generate_invoice_number(order.id)
            }
        )

        return invoice