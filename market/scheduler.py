import random
import threading
import time
from decimal import Decimal

from django.db import close_old_connections

from .models import Stock, StockPriceHistory


_running = False


def update_stocks():
    close_old_connections()

    stocks = Stock.objects.filter(
        random_enabled=True
    )

    for stock in stocks:

        stock.previous_price = stock.price

        # Random movement from -2% to +2%
        change_percent = Decimal(
            str(random.uniform(-0.02, 0.02))
        )

        new_price = stock.price * (
            Decimal("1.00") + change_percent
        )

        # Never go below ₹1
        if new_price < Decimal("1.00"):
            new_price = Decimal("1.00")

        stock.price = new_price.quantize(
            Decimal("0.01")
        )

        stock.save(
            update_fields=[
                "price",
                "previous_price"
            ]
        )

        # Save price history
        StockPriceHistory.objects.create(
            stock=stock,
            price=stock.price
        )

    close_old_connections()


def price_loop():
    global _running

    if _running:
        return

    _running = True

    while True:
        try:
            update_stocks()

        except Exception as e:
            print(
                "Stock update error:",
                e
            )

        time.sleep(2)


def start():
    global _running

    if _running:
        return

    thread = threading.Thread(
        target=price_loop,
        daemon=True
    )

    thread.start()