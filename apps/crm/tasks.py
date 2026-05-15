from __future__ import annotations
import logging
from celery import shared_task
from .models import Client, Product
logger = logging.getLogger(__name__)

@shared_task
def send_welcome_email(client_id: int) -> str:
    try:
        client = Client.objects.get(pk=client_id)
    except Client.DoesNotExist:
        message = f"welcome email skipped:client {client_id} does not exist"
        logger.warning(message)
        return message
    message = f"welcome email sent to {client.email}"
    logger.info(message)
    print(message)
    return message

@shared_task
def daily_stock_check() -> str:
    out_of_stock_products = Product.objects.filter(in_stock=False)
    count = out_of_stock_products.count()
    if count == 0:
        message = f"daily stock check complete:all products are in stock"
        logger.info(message)
        return message
    product_names = list(out_of_stock_products.values_list("name", flat=True))
    message = (
        f"daily stock alert: {count} product(s) out of stock: "
        f"{', '.join(product_names)}"
    )
    logger.warning(message)
    print(message)
    return message