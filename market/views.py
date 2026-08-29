from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from decimal import Decimal
import random

from .models import (
    Stock,
    Wallet,
    Holding,
    Transaction,
    MarketSettings,
)


# ==========================================
# MARKET HOME
# ==========================================

def home(request):

    stocks = Stock.objects.all()

    return render(
        request,
        "home.html",
        {
            "stocks": stocks
        }
    )


# ==========================================
# SIGNUP
# ==========================================

def signup(request):

    if request.method == "POST":

        form = UserCreationForm(request.POST)

        if form.is_valid():

            user = form.save()

            login(request, user)

            return redirect("market_home")

    else:

        form = UserCreationForm()

    return render(
        request,
        "signup.html",
        {
            "form": form
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

    # ======================================
    # MARKET OPEN / CLOSED
    # ======================================

    settings = MarketSettings.objects.first()

    if settings and not settings.market_open:

        messages.error(
            request,
            "🔴 Market is currently closed."
        )

        return render(
            request,
            "buy.html",
            {
                "stock": stock
            }
        )

    if request.method == "POST":

        try:
            quantity = int(
                request.POST.get(
                    "quantity",
                    0
                )
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

            # Remove money
            wallet.balance -= total
            wallet.save()

            # Get/create holding
            holding, created = Holding.objects.get_or_create(
                user=request.user,
                stock=stock
            )

            old_quantity = holding.quantity

            # First purchase
            if old_quantity == 0:

                holding.average_price = stock.price

            # Additional purchase
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

            # Save transaction
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

    # ======================================
    # MARKET OPEN / CLOSED
    # ======================================

    settings = MarketSettings.objects.first()

    if settings and not settings.market_open:

        messages.error(
            request,
            "🔴 Market is currently closed."
        )

        return render(
            request,
            "sell.html",
            {
                "stock": stock,
                "holding": holding
            }
        )

    if request.method == "POST":

        try:
            quantity = int(
                request.POST.get(
                    "quantity",
                    0
                )
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

            # Remove shares
            holding.quantity -= quantity

            if holding.quantity == 0:

                holding.delete()
                holding = None

            else:

                holding.save()

            # Add money
            wallet.balance += total

            wallet.save()

            # Save transaction
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

    holdings = Holding.objects.filter(
        user=request.user
    ).select_related(
        "stock"
    )

    transactions = Transaction.objects.filter(
        user=request.user
    ).select_related(
        "stock"
    ).order_by(
        "-created_at"
    )

    total_value = Decimal("0")
    total_invested = Decimal("0")
    total_pnl = Decimal("0")

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

    # JSON API request
    if request.GET.get("api") == "1":

        history = []

        try:

            from .models import StockPriceHistory

            prices = StockPriceHistory.objects.filter(
                stock=stock
            ).order_by(
                "created_at"
            )[:100]

            for item in prices:

                history.append({
                    "time": item.created_at.strftime(
                        "%H:%M:%S"
                    ),
                    "price": float(
                        item.price
                    ),
                })

        except Exception:

            history = []

        # Always have at least current price
        if not history:

            history.append({
                "time": timezone.localtime().strftime(
                    "%H:%M:%S"
                ),
                "price": float(
                    stock.price
                ),
            })

        return JsonResponse({
            "symbol": stock.symbol,
            "name": stock.name,
            "current_price": float(
                stock.price
            ),
            "data": history,
        })

    # Normal HTML page
    return render(
        request,
        "stock.html",
        {
            "symbol": stock.symbol,
            "stock": stock,
        }
    )


# ==========================================
# LIVE MARKET
# ==========================================

def live_market(request):

    return JsonResponse({
        "status": "live"
    })


# ==========================================
# STOCK PRICES API
# ==========================================

def stock_prices(request):

    stocks = Stock.objects.all()

    for stock in stocks:

        # Only move stocks that have
        # random movement enabled.
        if stock.random_enabled:

            old_price = stock.price

            # Random movement:
            # -2% to +2%
            movement = Decimal(
                str(
                    random.uniform(
                        -0.02,
                        0.02
                    )
                )
            )

            new_price = old_price * (
                Decimal("1.00") +
                movement
            )

            # Never below ₹1
            if new_price < Decimal("1.00"):

                new_price = Decimal("1.00")

            stock.previous_price = old_price

            stock.price = new_price.quantize(
                Decimal("0.01")
            )

            stock.save(
                update_fields=[
                    "price",
                    "previous_price"
                ]
            )

    # Get fresh prices
    stocks = Stock.objects.all()

    data = []

    for stock in stocks:

        data.append({
            "symbol": stock.symbol,
            "name": stock.name,
            "price": float(
                stock.price
            ),
            "previous_price": float(
                stock.previous_price
            ),
            "change": float(
                stock.change
            ),
            "change_percent": float(
                stock.change_percent
            ),
        })

    return JsonResponse({
        "stocks": data
    })