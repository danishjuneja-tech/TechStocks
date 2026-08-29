
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib import messages
from decimal import Decimal
import random
from django.http import JsonResponse
from django.core.cache import cache

from .models import Stock, Wallet, Holding, Transaction


# ==========================================
# MARKET HOME
# ==========================================

def home(request):


    stocks = Stock.objects.all()

    # AJAX price update
    if request.GET.get("prices") == "1":

        from django.http import JsonResponse

        data = {
            "stocks": [
                {
                    "symbol": stock.symbol,
                    "price": float(stock.price),
                    "change": float(stock.change),
                    "change_percent": float(stock.change_percent),
                }
                for stock in stocks
            ]
        }

        return JsonResponse(data)

    return render(
        request,
        "home.html",
        {
            "stocks": stocks
        }
    )




# ==========================================
# BUY STOCK
# ==========================================

@login_required
def buy_stock(request, symbol):

    stock = get_object_or_404(
        Stock,
        symbol=symbol
    )

    wallet, created = Wallet.objects.get_or_create(
        user=request.user
    )

    if request.method == "POST":

        try:
            quantity = int(
                request.POST.get("quantity", 0)
            )
        except (TypeError, ValueError):
            quantity = 0

        if quantity <= 0:
            messages.error(
                request,
                "Invalid quantity."
            )

            return render(
                request,
                "buy.html",
                {
                    "stock": stock
                }
            )

        total = stock.price * quantity

        if wallet.balance < total:
            messages.error(
                request,
                "Not enough virtual money."
            )

            return render(
                request,
                "buy.html",
                {
                    "stock": stock
                }
            )

        with transaction.atomic():

            wallet.balance -= total
            wallet.save()

            holding, created = Holding.objects.get_or_create(
                user=request.user,
                stock=stock
            )

            old_quantity = holding.quantity

            if old_quantity == 0:

                holding.average_price = stock.price

            else:

                old_value = (
                    holding.average_price *
                    old_quantity
                )

                new_value = (
                    stock.price *
                    quantity
                )

                holding.average_price = (
                    old_value + new_value
                ) / (
                    old_quantity + quantity
                )

            holding.quantity += quantity
            holding.save()

            Transaction.objects.create(
                user=request.user,
                stock=stock,
                transaction_type=Transaction.BUY,
                quantity=quantity,
                price=stock.price
            )

        messages.success(
            request,
            f"Bought {quantity} shares of {stock.symbol}."
        )

    return render(
        request,
        "buy.html",
        {
            "stock": stock
        }
    )


# ==========================================
# SELL STOCK
# ==========================================

@login_required
def sell_stock(request, symbol):

    stock = get_object_or_404(
        Stock,
        symbol=symbol
    )

    wallet, created = Wallet.objects.get_or_create(
        user=request.user
    )

    holding = Holding.objects.filter(
        user=request.user,
        stock=stock
    ).first()

    if request.method == "POST":

        try:
            quantity = int(
                request.POST.get("quantity", 0)
            )
        except (TypeError, ValueError):
            quantity = 0

        if quantity <= 0:

            messages.error(
                request,
                "Invalid quantity."
            )

            return render(
                request,
                "sell.html",
                {
                    "stock": stock,
                    "holding": holding
                }
            )

        if not holding or holding.quantity < quantity:

            messages.error(
                request,
                "You don't own enough shares."
            )

            return render(
                request,
                "sell.html",
                {
                    "stock": stock,
                    "holding": holding
                }
            )

        total = stock.price * quantity

        with transaction.atomic():

            holding.quantity -= quantity

            if holding.quantity == 0:

                holding.delete()
                holding = None

            else:

                holding.save()

            wallet.balance += total
            wallet.save()

            Transaction.objects.create(
                user=request.user,
                stock=stock,
                transaction_type=Transaction.SELL,
                quantity=quantity,
                price=stock.price
            )

        messages.success(
            request,
            f"Sold {quantity} shares of {stock.symbol}."
        )

    return render(
        request,
        "sell.html",
        {
            "stock": stock,
            "holding": holding
        }
    )


# ==========================================
# CUSTOMER PORTFOLIO
# ==========================================

@login_required
def portfolio(request):

    wallet, created = Wallet.objects.get_or_create(
        user=request.user
    )

    # Only this customer's holdings
    holdings = Holding.objects.filter(
        user=request.user
    ).select_related(
        "stock"
    )

    # Only this customer's transactions
    transactions = Transaction.objects.filter(
        user=request.user
    ).select_related(
        "stock"
    ).order_by(
        "-created_at"
    )

    total_value = 0
    total_invested = 0
    total_pnl = 0

    for holding in holdings:

        current_value = (
            holding.quantity *
            holding.stock.price
        )

        invested_value = (
            holding.quantity *
            holding.average_price
        )

        pnl = (
            current_value -
            invested_value
        )

        holding.current_value = current_value
        holding.invested_value = invested_value
        holding.pnl = pnl

        total_value += current_value
        total_invested += invested_value
        total_pnl += pnl

    return render(
        request,
        "portfolio.html",
        {
            "wallet": wallet,
            "holdings": holdings,
            "transactions": transactions,
            "total_value": total_value,
            "total_invested": total_invested,
            "total_pnl": total_pnl
        }
    )


# ==========================================
# STOCK GRAPH
# ==========================================

def stock_chart(request, symbol):

    stock = get_object_or_404(
        Stock,
        symbol=symbol
    )

    return render(
        request,
        "stock_chart.html",
        {
            "stock": stock
        }
    )
def stock_prices(request):

    # Only update the market once every 2 seconds
    lock = cache.add(
        "stock_market_update_lock",
        True,
        timeout=2
    )

    if lock:

        stocks = Stock.objects.filter(
            random_enabled=True
        )

        for stock in stocks:

            old_price = stock.price

            # Random movement between -5% and +5%
            movement = Decimal(
                str(random.uniform(-0.05, 0.05))
            )

            new_price = old_price * (
                Decimal("1.00") + movement
            )

            # Never go below ₹1
            if new_price < Decimal("1.00"):
                new_price = Decimal("1.00")

            stock.previous_price = old_price
            stock.price = new_price.quantize(
                Decimal("0.01")
            )

            stock.save()

    # Always return current prices
    stocks = Stock.objects.all()

    data = []

    for stock in stocks:

        data.append({
            "symbol": stock.symbol,
            "price": str(stock.price),
            "change": str(stock.change),
            "change_percent": float(
                stock.change_percent
            ),
        })

    return JsonResponse(
        data,
        safe=False
    )
