from django.urls import path
from . import views

urlpatterns = [

    # Market home
    path("", views.home, name="market_home"),

    # Signup
    path("signup/", views.signup, name="signup"),

    # Buy stock
    path("buy/<str:symbol>/", views.buy_stock, name="buy_stock"),

    # Sell stock
    path("sell/<str:symbol>/", views.sell_stock, name="sell_stock"),

    # Portfolio
    path("portfolio/", views.portfolio, name="portfolio"),

    # Stock graph
    path("stock/<str:symbol>/", views.stock_chart, name="stock_chart"),

    # Price API
    path("api/prices/", views.stock_prices, name="stock_prices"),

    # Live market API
    path("api/live/", views.live_market, name="live_market"),
]