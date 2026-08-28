from django.contrib import admin
from .models import Stock, Holding, Wallet, Transaction


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "symbol",
        "price",
        "previous_price",
        "random_enabled",
    )

    list_editable = (
        "price",
        "random_enabled",
    )

    search_fields = (
        "name",
        "symbol",
    )


@admin.register(Holding)
class HoldingAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "stock",
        "quantity",
        "average_price",
    )


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "balance",
    )


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "stock",
        "transaction_type",
        "quantity",
        "price",
        "created_at",
    )

    readonly_fields = (
        "created_at",
    )