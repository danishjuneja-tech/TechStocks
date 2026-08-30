
from django.contrib import admin

from .models import (
    Stock,
    StockPriceHistory,
    Holding,
    Wallet,
    Transaction,
    MarketSettings,
    LimitOrder,
)


# ==========================================
# STOCK
# ==========================================

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


# ==========================================
# STOCK PRICE HISTORY
# ==========================================

@admin.register(StockPriceHistory)
class StockPriceHistoryAdmin(admin.ModelAdmin):

    list_display = (
        "stock",
        "price",
        "created_at",
    )

    list_filter = (
        "stock",
    )

    readonly_fields = (
        "created_at",
    )


# ==========================================
# HOLDING
# ==========================================

@admin.register(Holding)
class HoldingAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "stock",
        "quantity",
        "average_price",
    )

    search_fields = (
        "user__username",
        "stock__symbol",
    )


# ==========================================
# WALLET
# ==========================================

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "balance",
    )

    search_fields = (
        "user__username",
    )


# ==========================================
# TRANSACTION
# ==========================================

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

    list_filter = (
        "transaction_type",
        "stock",
    )

    search_fields = (
        "user__username",
        "stock__symbol",
    )

    readonly_fields = (
        "created_at",
    )


# ==========================================
# MARKET SETTINGS
# ==========================================

@admin.register(MarketSettings)
class MarketSettingsAdmin(admin.ModelAdmin):

    list_display = (
        "market_open",
    )
@admin.register(LimitOrder)
class LimitOrderAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "stock",
        "order_type",
        "quantity",
        "limit_price",
        "executed",
        "created_at",
        "executed_at",
    )

    list_filter = (
        "executed",
        "stock",
        "order_type",
    )

    search_fields = (
        "user__username",
        "stock__symbol",
    )

    readonly_fields = (
        "created_at",
        "executed_at",
    )

