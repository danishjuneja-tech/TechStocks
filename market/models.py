from django.db import models
from django.contrib.auth.models import User


class Stock(models.Model):
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=20, unique=True)

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    previous_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    total_shares = models.PositiveIntegerField(
        default=1000000
    )

    sector = models.CharField(
        max_length=100,
        blank=True
    )

    description = models.TextField(
        blank=True
    )

    random_enabled = models.BooleanField(
        default=True
    )

    def __str__(self):
        return f"{self.name} ({self.symbol})"

    @property
    def change(self):
        return self.price - self.previous_price

    @property
    def change_percent(self):
        if self.previous_price == 0:
            return 0

        return (
            self.change /
            self.previous_price
        ) * 100


class StockPriceHistory(models.Model):
    stock = models.ForeignKey(
        Stock,
        on_delete=models.CASCADE,
        related_name="price_history"
    )

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return (
            f"{self.stock.symbol} "
            f"₹{self.price} "
            f"{self.created_at}"
        )


class Holding(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    stock = models.ForeignKey(
        Stock,
        on_delete=models.CASCADE
    )

    quantity = models.PositiveIntegerField(
        default=0
    )

    average_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    def __str__(self):
        return (
            f"{self.user.username} - "
            f"{self.stock.symbol}"
        )


class Wallet(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=100000
    )

    def __str__(self):
        return f"{self.user.username} Wallet"


class Transaction(models.Model):

    BUY = "BUY"
    SELL = "SELL"

    TYPES = [
        (BUY, "Buy"),
        (SELL, "Sell"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    stock = models.ForeignKey(
        Stock,
        on_delete=models.CASCADE
    )

    transaction_type = models.CharField(
        max_length=4,
        choices=TYPES
    )

    quantity = models.PositiveIntegerField()

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"{self.user.username} "
            f"{self.transaction_type} "
            f"{self.quantity} "
            f"{self.stock.symbol}"
        )


# ==========================================
# MARKET SETTINGS
# ==========================================

class MarketSettings(models.Model):

    market_open = models.BooleanField(
        default=True
    )

    def __str__(self):
        return "Market Settings"

