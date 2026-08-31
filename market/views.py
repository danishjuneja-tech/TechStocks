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
                "stock": stock,
                "wallet": wallet
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
            "stock": stock,
            "wallet": wallet
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
# REALIZED P&L CALCULATOR
# ==========================================

def calculate_realized_pnl(user):

    transactions = Transaction.objects.filter(
        user=user
    ).select_related(
        "stock"
    ).order_by(
        "created_at",
        "id"
    )

    # --------------------------------------
    # Store current cost basis for each stock
    # --------------------------------------

    positions = {}

    realized_pnl = Decimal("0")

    total_sell_value = Decimal("0")

    total_buy_value = Decimal("0")

    for txn in transactions:

        symbol = txn.stock.symbol

        # ----------------------------------
        # Create position if necessary
        # ----------------------------------

        if symbol not in positions:

            positions[symbol] = {
                "quantity": 0,
                "average_price": Decimal("0")
            }

        position = positions[symbol]

        # ==================================
        # BUY TRANSACTION
        # ==================================

        if txn.transaction_type == Transaction.BUY:

            old_quantity = position["quantity"]

            old_average = position["average_price"]

            buy_quantity = txn.quantity

            buy_price = txn.price

            old_value = (
                Decimal(old_quantity) *
                old_average
            )

            new_value = (
                Decimal(buy_quantity) *
                buy_price
            )

            new_quantity = (
                old_quantity +
                buy_quantity
            )

            if new_quantity > 0:

                position["average_price"] = (
                    old_value +
                    new_value
                ) / Decimal(new_quantity)

            position["quantity"] = new_quantity

            total_buy_value += new_value

        # ==================================
        # SELL TRANSACTION
        # ==================================

        elif txn.transaction_type == Transaction.SELL:

            sell_quantity = txn.quantity

            sell_price = txn.price

            # ----------------------------------
            # Average purchase price BEFORE SELL
            # ----------------------------------

            average_buy_price = position[
                "average_price"
            ]

            # ----------------------------------
            # Cost of shares being sold
            # ----------------------------------

            cost_of_sold_shares = (
                Decimal(sell_quantity) *
                average_buy_price
            )

            # ----------------------------------
            # Actual money received from sale
            # ----------------------------------

            sale_value = (
                Decimal(sell_quantity) *
                sell_price
            )

            # ----------------------------------
            # REALIZED PROFIT / LOSS
            # ----------------------------------

            sale_pnl = (
                sale_value -
                cost_of_sold_shares
            )

            realized_pnl += sale_pnl

            total_sell_value += sale_value

            # ----------------------------------
            # Remove sold shares from position
            # ----------------------------------

            position["quantity"] -= sell_quantity

            if position["quantity"] <= 0:

                position["quantity"] = 0

                position["average_price"] = Decimal("0")

    return {
        "realized_pnl": realized_pnl,
        "total_sell_value": total_sell_value,
        "total_buy_value": total_buy_value,
    }


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
    # CURRENT / UNREALIZED P&L
    # ======================================

    total_value = Decimal("0")

    total_invested = Decimal("0")

    unrealized_pnl = Decimal("0")

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

        unrealized_pnl += pnl

    # ======================================
    # REALIZED P&L
    # ======================================

    realized_data = calculate_realized_pnl(
        request.user
    )

    realized_pnl = realized_data[
        "realized_pnl"
    ]

    total_sell_value = realized_data[
        "total_sell_value"
    ]

    # ======================================
    # TOTAL P&L
    # ======================================

    total_pnl = (
        unrealized_pnl +
        realized_pnl
    )

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

            "total_pnl": total_pnl,

            "realized_pnl": realized_pnl,

            "unrealized_pnl": unrealized_pnl,

            "total_sell_value": total_sell_value,
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
    # UPDATE STOCK PRICES
    # ======================================

    for stock in stocks:

        if stock.random_enabled:

            old_price = stock.price

            # ==================================
            # NATURAL RANDOM MOVEMENT
            # ==================================

            movement = Decimal(
                str(
                    random.uniform(
                        -0.015,
                        0.015
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

            # ==================================
            # MINIMUM PRICE
            # ==================================

            if new_price < Decimal("1.00"):

                new_price = Decimal("1.00")

            # ==================================
            # SAVE PRICE
            # ==================================

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

            # ==================================
            # SAVE GRAPH HISTORY
            # ==================================

            StockPriceHistory.objects.create(
                stock=stock,
                price=stock.price
            )

    # ==========================================
    # EXECUTE PENDING LIMIT ORDERS
    # ==========================================

    pending_orders = LimitOrder.objects.filter(
        executed=False
    ).select_related(
        "user",
        "stock"
    )

    for order in pending_orders:

        stock = order.stock

        # ======================================
        # LIMIT BUY
        #
        # Executes when:
        #
        # current price <= limit price
        # ======================================

        if order.order_type == LimitOrder.BUY:

            if stock.price > order.limit_price:

                continue

            with transaction.atomic():

                # ----------------------------------
                # Wallet
                # ----------------------------------

                wallet, created = Wallet.objects.get_or_create(
                    user=order.user
                )

                # ----------------------------------
                # Buy at limit price
                # ----------------------------------

                buy_price = order.limit_price

                total = (
                    buy_price *
                    order.quantity
                )

                # ----------------------------------
                # Check wallet
                # ----------------------------------

                if wallet.balance < total:

                    continue

                # ----------------------------------
                # Deduct money
                # ----------------------------------

                wallet.balance -= total

                wallet.save()

                # ----------------------------------
                # Holding
                # ----------------------------------

                holding, created = Holding.objects.get_or_create(
                    user=order.user,
                    stock=stock
                )

                old_quantity = holding.quantity

                # ----------------------------------
                # First purchase
                # ----------------------------------

                if old_quantity == 0:

                    holding.average_price = buy_price

                # ----------------------------------
                # Additional purchase
                # ----------------------------------

                else:

                    old_value = (
                        holding.average_price *
                        old_quantity
                    )

                    new_value = (
                        buy_price *
                        order.quantity
                    )

                    holding.average_price = (
                        old_value +
                        new_value
                    ) / (
                        old_quantity +
                        order.quantity
                    )

                # ----------------------------------
                # Add shares
                # ----------------------------------

                holding.quantity += order.quantity

                holding.save()

                # ----------------------------------
                # Transaction history
                # ----------------------------------

                Transaction.objects.create(
                    user=order.user,
                    stock=stock,
                    transaction_type=Transaction.BUY,
                    quantity=order.quantity,
                    price=buy_price
                )

                # ----------------------------------
                # Mark executed
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
        # LIMIT SELL
        #
        # Executes when:
        #
        # current price >= limit price
        # ======================================

        elif order.order_type == LimitOrder.SELL:

            if stock.price < order.limit_price:

                continue

            with transaction.atomic():

                holding = Holding.objects.filter(
                    user=order.user,
                    stock=stock
                ).first()

                # ----------------------------------
                # Holding no longer exists
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
                # IMPORTANT:
                # Execute at CURRENT market price
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
                # Transaction history
                # ----------------------------------

                Transaction.objects.create(
                    user=order.user,
                    stock=stock,
                    transaction_type=Transaction.SELL,
                    quantity=order.quantity,
                    price=sell_price
                )

                # ----------------------------------
                # Mark executed
                # ----------------------------------

                order.executed = True

                order.executed_at = timezone.now()

                order.save(
                    update_fields=[
                        "executed",
                        "executed_at"
                    ]
                )

    # ==========================================
    # RETURN CURRENT PRICES
    # ==========================================

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


# ==========================================
# LIMIT BUY
# ==========================================

@login_required
def limit_buy(request, symbol):

    stock = get_object_or_404(
        Stock,
        symbol=symbol
    )

    wallet, created = Wallet.objects.get_or_create(
        user=request.user
    )

    settings = MarketSettings.objects.first()

    # ======================================
    # MARKET OPEN / CLOSED
    # ======================================

    if settings and not settings.market_open:

        messages.error(
            request,
            "🔴 Market is currently closed."
        )

        return render(
            request,
            "limit_buy.html",
            {
                "stock": stock,
                "wallet": wallet
            }
        )

    # ======================================
    # LIMIT BUY POST
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
                "limit_buy",
                symbol=stock.symbol
            )

        # ==================================
        # VALIDATE QUANTITY
        # ==================================

        if quantity <= 0:

            messages.error(
                request,
                "Quantity must be greater than 0."
            )

            return redirect(
                "limit_buy",
                symbol=stock.symbol
            )

        # ==================================
        # VALIDATE PRICE
        # ==================================

        if limit_price <= 0:

            messages.error(
                request,
                "Limit price must be greater than ₹0."
            )

            return redirect(
                "limit_buy",
                symbol=stock.symbol
            )

        # ==================================
        # LIMIT BUY MUST BE BELOW CURRENT
        # PRICE
        # ==================================

        if limit_price >= stock.price:

            messages.error(
                request,
                f"Limit buy price must be BELOW "
                f"the current price of ₹{stock.price}."
            )

            return redirect(
                "limit_buy",
                symbol=stock.symbol
            )

        # ==================================
        # CREATE LIMIT BUY
        #
        # Money is NOT deducted here.
        # Shares are NOT added here.
        # ==================================

        LimitOrder.objects.create(
            user=request.user,
            stock=stock,
            order_type=LimitOrder.BUY,
            quantity=quantity,
            limit_price=limit_price,
            executed=False
        )

        messages.success(
            request,
            f"🎯 Limit buy placed: "
            f"{quantity} shares of "
            f"{stock.symbol} at ₹{limit_price}."
        )

        return redirect(
            "limit_buy",
            symbol=stock.symbol
        )

    # ======================================
    # SHOW LIMIT BUY PAGE
    # ======================================

    return render(
        request,
        "limit_buy.html",
        {
            "stock": stock,
            "wallet": wallet
        }
    )
# ==========================================
# LIVE PORTFOLIO P&L API
# ==========================================

@login_required
def portfolio_prices(request):

    holdings = Holding.objects.filter(
        user=request.user
    ).select_related(
        "stock"
    )

    total_value = Decimal("0")
    total_invested = Decimal("0")

    data = []

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

        total_value += current_value
        total_invested += invested_value

        data.append({
            "symbol": holding.stock.symbol,
            "quantity": holding.quantity,
            "price": float(
                holding.stock.price
            ),
            "current_value": float(
                current_value
            ),
            "invested_value": float(
                invested_value
            ),
            "pnl": float(
                pnl
            ),
        })

    # ======================================
    # REALIZED P&L
    # ======================================

    realized_data = calculate_realized_pnl(
        request.user
    )

    realized_pnl = realized_data[
        "realized_pnl"
    ]

    total_sell_value = realized_data[
        "total_sell_value"
    ]

    # ======================================
    # UNREALIZED P&L
    # ======================================

    unrealized_pnl = (
        total_value -
        total_invested
    )

    # ======================================
    # TOTAL P&L
    # ======================================

    total_pnl = (
        unrealized_pnl +
        realized_pnl
    )

    return JsonResponse({

        "holdings": data,

        "total_value": float(
            total_value
        ),

        "total_invested": float(
            total_invested
        ),

        "unrealized_pnl": float(
            unrealized_pnl
        ),

        "realized_pnl": float(
            realized_pnl
        ),

        "total_pnl": float(
            total_pnl
        ),

        "total_sell_value": float(
            total_sell_value
        ),
    })