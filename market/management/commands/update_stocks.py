
from django.core.management.base import BaseCommand
from market.models import Stock
from decimal import Decimal
import random


class Command(BaseCommand):
    help = "Automatically changes stock prices randomly"

    def handle(self, *args, **options):

        stocks = Stock.objects.filter(random_enabled=True)

        for stock in stocks:

            stock.previous_price = stock.price

            change_percent = Decimal(
                str(random.uniform(-0.05, 0.05))
            )

            new_price = stock.price * (
                Decimal("1.00") + change_percent
            )

            if new_price < Decimal("1.00"):
                new_price = Decimal("1.00")

            stock.price = new_price.quantize(
                Decimal("0.01")
            )

            stock.save()

            self.stdout.write(
                f"{stock.symbol}: ₹{stock.previous_price} → ₹{stock.price}"
            )

