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

            Wallet.objects.get_or_create(
                user=user
            )

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

        if quantity <= 0:

            messages.error(
                request,
                "Invalid quantity."
            )

            return redirect(
                "buy_stock",
                symbol=stock.symbol
            )

        total = (
            stock.price *
            quantity
        )

        if wallet.balance < total:

            messages.error(
                request,
                "Not enough virtual money."
            )

            return redirect(
                "buy_stock",
                symbol=stock.symbol
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
                    old_value +
                    new_value
                ) / (
                    old_quantity +
                    quantity
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
            f"Bought {quantity} shares of "
            f"{stock.symbol} at ₹{stock.price}."
        )

        return redirect(
            "buy_stock",
            symbol=stock.symbol
        )

    return render(
        request,
        "buy.html",
        {
            "stock": stock,
            "wallet": wallet
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

        sell_price = stock.price

        total = (
            sell_price *
            quantity
        )

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

        if quantity <= 0:

            messages.error(
                request,
                "Quantity must be greater than 0."
            )

            return redirect(
                "limit_sell",
                symbol=stock.symbol
            )

        if limit_price <= 0:

            messages.error(
                request,
                "Limit price must be greater than ₹0."
            )

            return redirect(
                "limit_sell",
                symbol=stock.symbol
            )

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

        LimitOrder.objects.create(
            user=request.user,
            stock=stock,
            order_type=LimitOrder.SELL,
            quantity=quantity,
            limit_price=limit_price
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

    return render(
        request,
        "limit_sell.html",
        {
            "stock": stock,
            "holding": holding
        }
    )


# ==========================================
# REALIZED P&L
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

    positions = {}

    realized_pnl = Decimal("0")

    total_sell_value = Decimal("0")

    total_buy_value = Decimal("0")

    portfolio_details = {}

    for txn in transactions:

        symbol = txn.stock.symbol

        if symbol not in positions:

            positions[symbol] = {
                "quantity": 0,
                "average_price": Decimal("0")
            }

        if symbol not in portfolio_details:

            portfolio_details[symbol] = {
                "stock": txn.stock,
                "purchases": [],
                "sales": []
            }

        position = positions[symbol]

        # ======================================
        # BUY
        # ======================================

        if txn.transaction_type == Transaction.BUY:

            buy_quantity = txn.quantity

            buy_price = txn.price

            old_quantity = position["quantity"]

            old_average = position["average_price"]

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

            position["average_price"] = (
                old_value +
                new_value
            ) / Decimal(new_quantity)

            position["quantity"] = new_quantity

            total_buy_value += new_value

            portfolio_details[
                symbol
            ]["purchases"].append({

                "date": txn.created_at,

                "quantity": buy_quantity,

                "price": buy_price,

                "money": new_value
            })

        # ======================================
        # SELL
        # ======================================

        elif txn.transaction_type == Transaction.SELL:

            sell_quantity = txn.quantity

            sell_price = txn.price

            average_buy_price = position[
                "average_price"
            ]

            cost_of_sold_shares = (
                Decimal(sell_quantity) *
                average_buy_price
            )

            sale_value = (
                Decimal(sell_quantity) *
                sell_price
            )

            sale_pnl = (
                sale_value -
                cost_of_sold_shares
            )

            realized_pnl += sale_pnl

            total_sell_value += sale_value

            portfolio_details[
                symbol
            ]["sales"].append({

                "date": txn.created_at,

                "quantity": sell_quantity,

                "price": sell_price,

                "money": sale_value,

                "cost": cost_of_sold_shares,

                "pnl": sale_pnl
            })

            position["quantity"] -= sell_quantity

            if position["quantity"] <= 0:

                position["quantity"] = 0

                position["average_price"] = Decimal("0")

    return {

        "realized_pnl": realized_pnl,

        "total_sell_value": total_sell_value,

        "total_buy_value": total_buy_value,

        "portfolio_details": portfolio_details
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

    pending_orders = LimitOrder.objects.filter(
        user=request.user,
        executed=False
    ).select_related(
        "stock"
    ).order_by(
        "-created_at"
    )

    total_value = Decimal("0")

    total_invested = Decimal("0")

    unrealized_pnl = Decimal("0")

    for holding in holdings:

        current_price = holding.stock.price

        current_value = (
            Decimal(holding.quantity) *
            current_price
        )

        invested_value = (
            Decimal(holding.quantity) *
            holding.average_price
        )

        pnl = (
            current_value -
            invested_value
        )

        holding.current_price = current_price

        holding.current_value = current_value

        holding.invested_value = invested_value

        holding.pnl = pnl

        # NEW
        holding.pnl_per_share = (
            current_price -
            holding.average_price
        )

        total_value += current_value

        total_invested += invested_value

        unrealized_pnl += pnl

    realized_data = calculate_realized_pnl(
        request.user
    )

    realized_pnl = realized_data[
        "realized_pnl"
    ]

    total_sell_value = realized_data[
        "total_sell_value"
    ]

    portfolio_details = realized_data[
        "portfolio_details"
    ]

    total_pnl = (
        unrealized_pnl +
        realized_pnl
    )

    today = timezone.localdate()

    today_realized_pnl = Decimal("0")

    today_unrealized_pnl = Decimal("0")

    for details in portfolio_details.values():

        for sale in details["sales"]:

            sale_date = timezone.localtime(
                sale["date"]
            ).date()

            if sale_date == today:

                today_realized_pnl += sale["pnl"]

    for holding in holdings:

        today_unrealized_pnl += (

            holding.stock.price -
            holding.stock.previous_price

        ) * Decimal(holding.quantity)

    today_pnl = (
        today_realized_pnl +
        today_unrealized_pnl
    )

    portfolio2 = []

    for symbol, details in portfolio_details.items():

        stock = details["stock"]

        holding = Holding.objects.filter(
            user=request.user,
            stock=stock
        ).first()

        current_quantity = 0

        average_price = Decimal("0")

        current_value = Decimal("0")

        invested_value = Decimal("0")

        current_pnl = Decimal("0")

        pnl_per_share = Decimal("0")

        if holding:

            current_quantity = holding.quantity

            average_price = holding.average_price

            current_value = (
                Decimal(current_quantity) *
                stock.price
            )

            invested_value = (
                Decimal(current_quantity) *
                average_price
            )

            current_pnl = (
                current_value -
                invested_value
            )

            # NEW
            pnl_per_share = (
                stock.price -
                average_price
            )

        total_purchased_shares = 0

        total_purchase_money = Decimal("0")

        for purchase in details["purchases"]:

            total_purchased_shares += (
                purchase["quantity"]
            )

            total_purchase_money += (
                purchase["money"]
            )

        total_sold_shares = 0

        total_sale_money = Decimal("0")

        stock_realized_pnl = Decimal("0")

        for sale in details["sales"]:

            total_sold_shares += (
                sale["quantity"]
            )

            total_sale_money += (
                sale["money"]
            )

            stock_realized_pnl += (
                sale["pnl"]
            )

        portfolio2.append({

            "stock": stock,

            "symbol": symbol,

            "purchases": details["purchases"],

            "total_purchased_shares":
                total_purchased_shares,

            "total_purchase_money":
                total_purchase_money,

            "sales": details["sales"],

            "total_sold_shares":
                total_sold_shares,

            "total_sale_money":
                total_sale_money,

            "stock_realized_pnl":
                stock_realized_pnl,

            "current_quantity":
                current_quantity,

            "average_price":
                average_price,

            "current_price":
                stock.price,

            "current_value":
                current_value,

            "invested_value":
                invested_value,

            "current_pnl":
                current_pnl,

            # NEW
            "pnl_per_share":
                pnl_per_share,
        })

    return render(
        request,
        "portfolio.html",
        {

            "wallet": wallet,

            "holdings": holdings,

            "total_value": total_value,

            "total_invested": total_invested,

            "realized_pnl": realized_pnl,

            "unrealized_pnl": unrealized_pnl,

            "total_pnl": total_pnl,

            "total_sell_value": total_sell_value,

            "today_pnl": today_pnl,

            "today_realized_pnl":
                today_realized_pnl,

            "today_unrealized_pnl":
                today_unrealized_pnl,

            "transactions": transactions,

            "pending_orders": pending_orders,

            "portfolio2": portfolio2,
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

    if request.GET.get("api") == "1":

        history = []

        prices = StockPriceHistory.objects.filter(
            stock=stock
        ).order_by(
            "created_at"
        )[:100]

        for item in prices:

            history.append({

                "time":
                    item.created_at.strftime(
                        "%H:%M:%S"
                    ),

                "price":
                    float(item.price)
            })

        if not history:

            history.append({

                "time":
                    timezone.localtime().strftime(
                        "%H:%M:%S"
                    ),

                "price":
                    float(stock.price)
            })

        return JsonResponse({

            "symbol":
                stock.symbol,

            "name":
                stock.name,

            "current_price":
                float(stock.price),

            "data":
                history
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
# STOCK PRICES + LIMIT ORDERS
# ==========================================

def stock_prices(request):

    stocks = Stock.objects.all()

    # ======================================
    # UPDATE PRICES
    # ======================================

    for stock in stocks:

        if stock.random_enabled:

            old_price = stock.price

            movement_percent = random.choices(
                [
                    Decimal("0.02"),
                    Decimal("0.05"),
                    Decimal("0.10")
                ],
                weights=[
                    40,
                    40,
                    20
                ],
                k=1
            )[0]

            if random.choice([True, False]):

                movement = movement_percent

            else:

                movement = -movement_percent

            new_price = old_price * (
                Decimal("1.00") +
                movement
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

            StockPriceHistory.objects.create(
                stock=stock,
                price=stock.price
            )

    # ======================================
    # EXECUTE LIMIT ORDERS
    # ======================================

    pending_orders = LimitOrder.objects.filter(
        executed=False
    ).select_related(
        "user",
        "stock"
    )

    for order in pending_orders:

        stock = order.stock

        # ==================================
        # LIMIT BUY
        # ==================================

        if order.order_type == LimitOrder.BUY:

            if stock.price > order.limit_price:

                continue

            with transaction.atomic():

                wallet, created = Wallet.objects.get_or_create(
                    user=order.user
                )

                buy_price = stock.price

                total = (
                    buy_price *
                    order.quantity
                )

                if wallet.balance < total:

                    continue

                wallet.balance -= total

                wallet.save()

                holding, created = Holding.objects.get_or_create(
                    user=order.user,
                    stock=stock
                )

                old_quantity = holding.quantity

                if old_quantity == 0:

                    holding.average_price = buy_price

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

                holding.quantity += order.quantity

                holding.save()

                Transaction.objects.create(
                    user=order.user,
                    stock=stock,
                    transaction_type=Transaction.BUY,
                    quantity=order.quantity,
                    price=buy_price
                )

                order.executed = True

                order.executed_at = timezone.now()

                order.save(
                    update_fields=[
                        "executed",
                        "executed_at"
                    ]
                )

        # ==================================
        # LIMIT SELL
        # ==================================

        elif order.order_type == LimitOrder.SELL:

            if stock.price < order.limit_price:

                continue

            with transaction.atomic():

                holding = Holding.objects.filter(
                    user=order.user,
                    stock=stock
                ).first()

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

                wallet, created = Wallet.objects.get_or_create(
                    user=order.user
                )

                sell_price = stock.price

                total = (
                    sell_price *
                    order.quantity
                )

                holding.quantity -= order.quantity

                if holding.quantity == 0:

                    holding.delete()

                else:

                    holding.save()

                wallet.balance += total

                wallet.save()

                Transaction.objects.create(
                    user=order.user,
                    stock=stock,
                    transaction_type=Transaction.SELL,
                    quantity=order.quantity,
                    price=sell_price
                )

                order.executed = True

                order.executed_at = timezone.now()

                order.save(
                    update_fields=[
                        "executed",
                        "executed_at"
                    ]
                )

    # ======================================
    # RETURN PRICES
    # ======================================

    data = []

    for stock in Stock.objects.all():

        data.append({

            "symbol":
                stock.symbol,

            "name":
                stock.name,

            "price":
                float(stock.price),

            "previous_price":
                float(stock.previous_price),

            "change":
                float(stock.change),

            "change_percent":
                float(stock.change_percent)
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

        return redirect(
            "portfolio"
        )

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

    return redirect(
        "portfolio"
    )


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

        if quantity <= 0:

            messages.error(
                request,
                "Quantity must be greater than 0."
            )

            return redirect(
                "limit_buy",
                symbol=stock.symbol
            )

        if limit_price <= 0:

            messages.error(
                request,
                "Limit price must be greater than ₹0."
            )

            return redirect(
                "limit_buy",
                symbol=stock.symbol
            )

        total = (
            limit_price *
            quantity
        )

        if wallet.balance < total:

            messages.error(
                request,
                "Not enough virtual money for this order."
            )

            return redirect(
                "limit_buy",
                symbol=stock.symbol
            )

        # ==================================
        # IMMEDIATE EXECUTION
        # ==================================

        if stock.price <= limit_price:

            buy_price = stock.price

            total = (
                buy_price *
                quantity
            )

            if wallet.balance < total:

                messages.error(
                    request,
                    "Not enough virtual money."
                )

                return redirect(
                    "limit_buy",
                    symbol=stock.symbol
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

                    holding.average_price = buy_price

                else:

                    old_value = (
                        holding.average_price *
                        old_quantity
                    )

                    new_value = (
                        buy_price *
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

                Transaction.objects.create(
                    user=request.user,
                    stock=stock,
                    transaction_type=Transaction.BUY,
                    quantity=quantity,
                    price=buy_price
                )

            messages.success(
                request,
                f"✅ Bought {quantity} shares of "
                f"{stock.symbol} at ₹{buy_price}."
            )

            return redirect(
                "limit_buy",
                symbol=stock.symbol
            )

        # ==================================
        # PENDING ORDER
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

        # ======================================
        # LIVE PRICE
        # ======================================

        current_price = holding.stock.price

        # ======================================
        # CURRENT VALUE
        # ======================================

        current_value = (
            Decimal(holding.quantity) *
            current_price
        )

        # ======================================
        # INVESTED VALUE
        # ======================================

        invested_value = (
            Decimal(holding.quantity) *
            holding.average_price
        )

        # ======================================
        # P&L PER SHARE
        # ======================================

        pnl_per_share = (
            current_price -
            holding.average_price
        )

        # ======================================
        # TOTAL P&L
        # ======================================

        pnl = (
            current_value -
            invested_value
        )

        total_value += current_value

        total_invested += invested_value

        data.append({

            "symbol":
                holding.stock.symbol,

            "quantity":
                holding.quantity,

            "price":
                float(current_price),

            "average_price":
                float(holding.average_price),

            "pnl_per_share":
                float(pnl_per_share),

            "current_value":
                float(current_value),

            "invested_value":
                float(invested_value),

            "pnl":
                float(pnl)
        })

    # ==========================================
    # REALIZED P&L
    # ==========================================

    realized_data = calculate_realized_pnl(
        request.user
    )

    realized_pnl = realized_data[
        "realized_pnl"
    ]

    total_sell_value = realized_data[
        "total_sell_value"
    ]

    # ==========================================
    # UNREALIZED P&L
    # ==========================================

    unrealized_pnl = (
        total_value -
        total_invested
    )

    # ==========================================
    # TOTAL P&L
    # ==========================================

    total_pnl = (
        unrealized_pnl +
        realized_pnl
    )

    # ==========================================
    # TODAY'S P&L
    # ==========================================

    today = timezone.localdate()

    today_realized_pnl = Decimal("0")

    today_unrealized_pnl = Decimal("0")

    for details in realized_data[
        "portfolio_details"
    ].values():

        for sale in details["sales"]:

            sale_date = timezone.localtime(
                sale["date"]
            ).date()

            if sale_date == today:

                today_realized_pnl += sale["pnl"]

    # ==========================================
    # TODAY'S UNREALIZED
    # ==========================================

    for holding in holdings:

        today_unrealized_pnl += (

            holding.stock.price -
            holding.stock.previous_price

        ) * Decimal(holding.quantity)

    # ==========================================
    # TODAY'S TOTAL
    # ==========================================

    today_pnl = (
        today_realized_pnl +
        today_unrealized_pnl
    )

    return JsonResponse({

        # ======================================
        # HOLDINGS
        # ======================================

        "holdings":
            data,

        # ======================================
        # PORTFOLIO TOTALS
        # ======================================

        "total_value":
            float(total_value),

        "total_invested":
            float(total_invested),

        "unrealized_pnl":
            float(unrealized_pnl),

        "realized_pnl":
            float(realized_pnl),

        "total_pnl":
            float(total_pnl),

        "total_sell_value":
            float(total_sell_value),

        # ======================================
        # TODAY
        # ======================================

        "today_pnl":
            float(today_pnl),

        "today_realized_pnl":
            float(today_realized_pnl),

        "today_unrealized_pnl":
            float(today_unrealized_pnl)
    })