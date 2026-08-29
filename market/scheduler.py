import random
import threading
import time
from decimal import Decimal

from django.db import close_old_connections

from .models import Stock, StockPriceHistory


_running = False
_thread = None
_lock = threading.Lock()


def update_stocks():

    close_old_connections()

    try:

        stocks = Stock.objects.filter(
            random_enabled=True
        )

        for stock in stocks:

            old_price = stock.price

            stock.previous_price = old_price

            change_percent = Decimal(
                str(random.uniform(-0.02, 0.02))
            )

            new_price = old_price * (
                Decimal("1.00") + change_percent
            )

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

            StockPriceHistory.objects.create(
                stock=stock,
                price=stock.price
            )

            print(
                f"📈 {stock.symbol}: "
                f"₹{old_price} → ₹{stock.price}"
            )

    finally:

        close_old_connections()


def price_loop():

    global _running

    while _running:

        try:

            update_stocks()

        except Exception as e:

            print(
                "Stock update error:",
                e
            )

        # Update every 2 seconds
        for _ in range(20):

            if not _running:
                break

            time.sleep(0.1)


def start():

    global _running
    global _thread

    with _lock:

        if _running:
            return

        _running = True

        _thread = threading.Thread(
            target=price_loop,
            daemon=True
        )

        _thread.start()

        print("🟢 Live stock updater started")


def stop():

    global _running

    _running = False

    print("🔴 Live stock updater stopped")


def is_running():

    return _running