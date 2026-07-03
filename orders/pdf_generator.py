from io import BytesIO

from reportlab.pdfgen import canvas


class InvoicePDFGenerator:

    @staticmethod
    def generate(invoice):

        buffer = BytesIO()

        pdf = canvas.Canvas(buffer)

        pdf.setTitle(invoice.invoice_number)

        pdf.drawString(
            100,
            800,
            f"Invoice: {invoice.invoice_number}"
        )

        pdf.drawString(
            100,
            780,
            f"Order ID: {invoice.order.id}"
        )

        pdf.drawString(
            100,
            760,
            f"Customer: {invoice.order.customer.username}"
        )

        pdf.drawString(
            100,
            740,
            f"Total: Rs. {invoice.order.total_amount}"
        )

        pdf.save()

        buffer.seek(0)

        return buffer