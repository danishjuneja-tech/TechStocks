from django.urls import path
from . import views


urlpatterns = [

    # ==========================================
    # HOME
    # ==========================================

    path(
        "",
        views.home,
        name="market_home"
    ),



    # ==========================================
    # BUY
    # ==========================================

    path(
        "buy/<str:symbol>/",
        views.buy_stock,
        name="buy_stock"
    ),

    # ==========================================
    # SELL
    # ==========================================

    path(
        "sell/<str:symbol>/",
        views.sell_stock,
        name="sell_stock"
    ),

    # ==========================================
    # LIMIT SELL
    # ==========================================

    path(
        "sell/<str:symbol>/limit/",
        views.limit_sell,
        name="limit_sell"
    ),

    # ==========================================
    # LIMIT BUY
    # ==========================================

    path(
        "buy/<str:symbol>/limit/",
        views.limit_buy,
        name="limit_buy"
    ),

    # ==========================================
    # CANCEL LIMIT ORDER
    # ==========================================

    path(
        "limit-order/cancel/<int:order_id>/",
        views.cancel_limit_order,
        name="cancel_limit_order"
    ),

    # ==========================================
    # PORTFOLIO
    # ==========================================

    path(
        "portfolio/",
        views.portfolio,
        name="portfolio"
    ),

    # ==========================================
    # STOCK CHART
    # ==========================================

    path(
        "stock/<str:symbol>/",
        views.stock_chart,
        name="stock_chart"
    ),

    # ==========================================
    # LIVE MARKET
    # ==========================================

    path(
        "live/",
        views.live_market,
        name="live_market"
    ),

    # ==========================================
    # STOCK PRICES
    # ==========================================

    path(
        "prices/",
        views.stock_prices,
        name="stock_prices"
    ),
    path(
    "signup/",
    views.signup,
    name="signup"
),
path(
    "portfolio/prices/",
    views.portfolio_prices,
    name="portfolio_prices"
),
]