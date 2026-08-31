
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect


urlpatterns = [

    # Website root → Market
    path(
        "",
        lambda request: redirect("market_home")
    ),

    # Market
    path(
        "market/",
        include("market.urls")
    ),

    # Admin
    path(
        "admin/",
        admin.site.urls
    ),

    # Login / Logout
    path(
        "accounts/",
        include("django.contrib.auth.urls")
    ),

]

