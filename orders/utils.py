from datetime import datetime


def generate_invoice_number(order_id):
    return f"INV-{datetime.now().strftime('%Y%m%d')}-{order_id}"