
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone

from decimal import Decimal
import random

from .models import (
    Stock,
    StockPriceHistory,
    Wallet,
    Holding,
    Transaction,
    LimitOrder,
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

    # ======================================
    # BUY
    # ======================================

    if request.method == "POST":

        try:

            quantity = int(
                request.POST.get(
                    "quantity",
                    0
                )
            )

        except (
            TypeError,
            ValueError
        ):

            quantity = 0

        # ----------------------------------
        # Validate quantity
        # ----------------------------------

        if quantity <= 0:

            messages.error(
                request,
                "Invalid quantity."
            )

            return redirect(
                "buy_stock",
                symbol=stock.symbol
            )

        # ----------------------------------
        # Calculate total
        # ----------------------------------

        total = (
            stock.price *
            quantity
        )

        # ----------------------------------
        # Check wallet
        # ----------------------------------

        if wallet.balance < total:

            messages.error(
                request,
                "Not enough virtual money."
            )

            return redirect(
                "buy_stock",
                symbol=stock.symbol
            )

        # ==================================
        # COMPLETE BUY
        # ==================================

        with transaction.atomic():

            wallet.balance -= total

            wallet.save()

            holding, created = Holding.objects.get_or_create(
                user=request.user,
                stock=stock
            )

            old_quantity = holding.quantity

            # --------------------------------
            # First purchase
            # --------------------------------

            if old_quantity == 0:

                holding.average_price = stock.price

            # --------------------------------
            # Additional purchase
            # --------------------------------

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
                    old_value +
                    new_value
                ) / (
                    old_quantity +
                    quantity
                )

            holding.quantity += quantity

            holding.save()

            # --------------------------------
            # Transaction history
            # --------------------------------

            Transaction.objects.create(
                user=request.user,
                stock=stock,
                transaction_type=Transaction.BUY,
                quantity=quantity,
                price=stock.price
            )

        messages.success(
            request,
            f"Bought {quantity} shares of "
            f"{stock.symbol} at ₹{stock.price}."
        )

        return redirect(
            "buy_stock",
            symbol=stock.symbol
        )

    # ======================================
    # SHOW BUY PAGE
    # ======================================

    return render(
        request,
        "buy.html",
        {
            "stock": stock
        }
    )


# ==========================================
# MARKET SELL
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

    # ======================================
    # MARKET SELL
    # ======================================

    if request.method == "POST":

        sell_type = request.POST.get(
            "sell_type",
            "market"
        )

        if sell_type != "market":

            return redirect(
                "limit_sell",
                symbol=stock.symbol
            )

        try:

            quantity = int(
                request.POST.get(
                    "quantity",
                    0
                )
            )

        except (
            TypeError,
            ValueError
        ):

            quantity = 0

        if quantity <= 0:

            messages.error(
                request,
                "Invalid quantity."
            )

            return redirect(
                "sell_stock",
                symbol=stock.symbol
            )

        if not holding:

            messages.error(
                request,
                "You don't own this stock."
            )

            return redirect(
                "sell_stock",
                symbol=stock.symbol
            )

        if holding.quantity < quantity:

            messages.error(
                request,
                "You don't own enough shares."
            )

            return redirect(
                "sell_stock",
                symbol=stock.symbol
            )

        # ----------------------------------
        # Current market price
        # ----------------------------------

        sell_price = stock.price

        total = (
            sell_price *
            quantity
        )

        # ==================================
        # COMPLETE SELL
        # ==================================

        with transaction.atomic():

            holding.quantity -= quantity

            if holding.quantity == 0:

                holding.delete()

            else:

                holding.save()

            wallet.balance += total

            wallet.save()

            Transaction.objects.create(
                user=request.user,
                stock=stock,
                transaction_type=Transaction.SELL,
                quantity=quantity,
                price=sell_price
            )

        messages.success(
            request,
            f"Sold {quantity} shares of "
            f"{stock.symbol} at ₹{sell_price}."
        )

        return redirect(
            "sell_stock",
            symbol=stock.symbol
        )

    # ======================================
    # SELL PAGE
    # ======================================

    return render(
        request,
        "sell.html",
        {
            "stock": stock,
            "holding": holding
        }
    )


# ==========================================
# LIMIT SELL
# ==========================================

@login_required
def limit_sell(request, symbol):

    stock = get_object_or_404(
        Stock,
        symbol=symbol
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
            "limit_sell.html",
            {
                "stock": stock,
                "holding": holding
            }
        )

    # ======================================
    # CREATE LIMIT ORDER
    # ======================================

    if request.method == "POST":

        try:

            quantity = int(
                request.POST.get(
                    "quantity",
                    0
                )
            )

            limit_price = Decimal(
                request.POST.get(
                    "limit_price",
                    "0"
                )
            )

        except (
            TypeError,
            ValueError,
            ArithmeticError
        ):

            messages.error(
                request,
                "Invalid quantity or limit price."
            )

            return redirect(
                "limit_sell",
                symbol=stock.symbol
            )

        # ----------------------------------
        # Quantity
        # ----------------------------------

        if quantity <= 0:

            messages.error(
                request,
                "Quantity must be greater than 0."
            )

            return redirect(
                "limit_sell",
                symbol=stock.symbol
            )

        # ----------------------------------
        # Price
        # ----------------------------------

        if limit_price <= 0:

            messages.error(
                request,
                "Limit price must be greater than ₹0."
            )

            return redirect(
                "limit_sell",
                symbol=stock.symbol
            )

        # ----------------------------------
        # Holding
        # ----------------------------------

        if not holding:

            messages.error(
                request,
                "You don't own this stock."
            )

            return redirect(
                "limit_sell",
                symbol=stock.symbol
            )

        if holding.quantity < quantity:

            messages.error(
                request,
                "You don't own enough shares."
            )

            return redirect(
                "limit_sell",
                symbol=stock.symbol
            )

        # ----------------------------------
        # Target must be above current
        # ----------------------------------

        if limit_price <= stock.price:

            messages.error(
                request,
                f"Limit price must be ABOVE "
                f"current price ₹{stock.price}."
            )

            return redirect(
                "limit_sell",
                symbol=stock.symbol
            )

        # ==================================
        # CREATE ORDER
        # ==================================

        LimitOrder.objects.create(
            user=request.user,
            stock=stock,
            order_type=LimitOrder.SELL,
            quantity=quantity,
            limit_price=limit_price,
            executed=False
        )

        messages.success(
            request,
            f"🎯 Limit sell placed: "
            f"{quantity} shares of "
            f"{stock.symbol} at ₹{limit_price}."
        )

        return redirect(
            "limit_sell",
            symbol=stock.symbol
        )

    # ======================================
    # LIMIT SELL PAGE
    # ======================================

    return render(
        request,
        "limit_sell.html",
        {
            "stock": stock,
            "holding": holding
        }
    )


# ==========================================
# PORTFOLIO
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

    # ======================================
    # PENDING ORDERS
    # ======================================

    pending_orders = LimitOrder.objects.filter(
        user=request.user,
        executed=False
    ).select_related(
        "stock"
    ).order_by(
        "-created_at"
    )

    # ======================================
    # CALCULATE PORTFOLIO
    # ======================================

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

    # ======================================
    # PORTFOLIO PAGE
    # ======================================

    return render(
        request,
        "portfolio.html",
        {
            "wallet": wallet,

            "holdings": holdings,

            "transactions": transactions,

            "pending_orders": pending_orders,

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

    # ======================================
    # GRAPH API
    # ======================================

    if request.GET.get("api") == "1":

        history = []

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
                )
            })

        if not history:

            history.append({
                "time": timezone.localtime().strftime(
                    "%H:%M:%S"
                ),
                "price": float(
                    stock.price
                )
            })

        return JsonResponse({
            "symbol": stock.symbol,
            "name": stock.name,
            "current_price": float(
                stock.price
            ),
            "data": history
        })

    return render(
        request,
        "stock.html",
        {
            "symbol": stock.symbol,
            "stock": stock
        }
    )


# ==========================================
# LIVE MARKET STATUS
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

    # ======================================
    # UPDATE PRICES
    # ======================================

    for stock in stocks:

        if stock.random_enabled:

            old_price = stock.price

            movement = Decimal(
                str(
                    random.uniform(
                        -0.02,
                        0.02
                    )
                )
            )

            new_price = (
                old_price *
                (
                    Decimal("1.00") +
                    movement
                )
            )

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

            # ----------------------------------
            # History
            # ----------------------------------

            StockPriceHistory.objects.create(
                stock=stock,
                price=stock.price
            )

    # ======================================
    # EXECUTE LIMIT ORDERS
    # ======================================

    pending_orders = LimitOrder.objects.filter(
        executed=False,
        order_type=LimitOrder.SELL
    ).select_related(
        "user",
        "stock"
    )

    for order in pending_orders:

        stock = order.stock

        # ----------------------------------
        # Target not reached
        # ----------------------------------

        if stock.price < order.limit_price:

            continue

        with transaction.atomic():

            holding = Holding.objects.filter(
                user=order.user,
                stock=stock
            ).first()

            # ----------------------------------
            # Holding missing
            # ----------------------------------

            if not holding:

                order.executed = True

                order.executed_at = timezone.now()

                order.save(
                    update_fields=[
                        "executed",
                        "executed_at"
                    ]
                )

                continue

            # ----------------------------------
            # Not enough shares
            # ----------------------------------

            if holding.quantity < order.quantity:

                order.executed = True

                order.executed_at = timezone.now()

                order.save(
                    update_fields=[
                        "executed",
                        "executed_at"
                    ]
                )

                continue

            # ----------------------------------
            # Wallet
            # ----------------------------------

            wallet, created = Wallet.objects.get_or_create(
                user=order.user
            )

            # ----------------------------------
            # Execute at current price
            # ----------------------------------

            sell_price = stock.price

            total = (
                sell_price *
                order.quantity
            )

            # ----------------------------------
            # Remove shares
            # ----------------------------------

            holding.quantity -= order.quantity

            if holding.quantity == 0:

                holding.delete()

            else:

                holding.save()

            # ----------------------------------
            # Add money
            # ----------------------------------

            wallet.balance += total

            wallet.save()

            # ----------------------------------
            # Transaction
            # ----------------------------------

            Transaction.objects.create(
                user=order.user,
                stock=stock,
                transaction_type=Transaction.SELL,
                quantity=order.quantity,
                price=sell_price
            )

            # ----------------------------------
            # Complete order
            # ----------------------------------

            order.executed = True

            order.executed_at = timezone.now()

            order.save(
                update_fields=[
                    "executed",
                    "executed_at"
                ]
            )

    # ======================================
    # RETURN LIVE PRICES
    # ======================================

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
            )
        })

    return JsonResponse({
        "stocks": data
    })


# ==========================================
# CANCEL LIMIT ORDER
# ==========================================

@login_required
def cancel_limit_order(request, order_id):

    if request.method != "POST":

        return redirect("portfolio")

    order = get_object_or_404(
        LimitOrder,
        id=order_id,
        user=request.user,
        executed=False
    )

    quantity = order.quantity

    symbol = order.stock.symbol

    order.delete()

    messages.success(
        request,
        f"❌ Limit order cancelled for "
        f"{quantity} shares of {symbol}."
    )

    return redirect("portfolio")

