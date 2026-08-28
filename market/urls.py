from django.urls import path
from . import views


urlpatterns = [

    path(
        "",
        views.home,
        name="market_home"
    ),

    path(
        "buy/<str:symbol>/",
        views.buy_stock,
        name="buy_stock"
    ),

    path(
        "sell/<str:symbol>/",
        views.sell_stock,
        name="sell_stock"
    ),

    path(
        "portfolio/",
        views.portfolio,
        name="portfolio"
    ),

    path(
        "stock/<str:symbol>/",
        views.stock_chart,
        name="stock_chart"
    ),
]