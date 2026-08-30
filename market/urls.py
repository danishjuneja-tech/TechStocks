
from django.urls import path
from . import views


urlpatterns = [

    # Home
    path(
        "",
        views.home,
        name="market_home"
    ),

    # Buy
    path(
        "buy/<str:symbol>/",
        views.buy_stock,
        name="buy_stock"
    ),

    # Immediate Sell
    path(
        "sell/<str:symbol>/",
        views.sell_stock,
        name="sell_stock"
    ),

    # Limit Sell
    path(
        "sell/<str:symbol>/limit/",
        views.limit_sell,
        name="limit_sell"
    ),

    # Cancel Limit Order
    path(
        "limit-order/cancel/<int:order_id>/",
        views.cancel_limit_order,
        name="cancel_limit_order"
    ),

    # Portfolio
    path(
        "portfolio/",
        views.portfolio,
        name="portfolio"
    ),

    # Stock chart
    path(
        "stock/<str:symbol>/",
        views.stock_chart,
        name="stock_chart"
    ),

    # Live market
    path(
        "live/",
        views.live_market,
        name="live_market"
    ),

    # Stock prices API
    path(
        "prices/",
        views.stock_prices,
        name="stock_prices"
    ),

]

