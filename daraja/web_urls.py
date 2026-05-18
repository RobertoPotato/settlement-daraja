from django.urls import path

from . import web_views

urlpatterns = [
    path("", web_views.LandingPageView.as_view(), name="landing"),
    path("home/", web_views.DarajaTestHomeView.as_view(), name="home"),
    path("paybills/new/", web_views.DarajaPaybillCreateView.as_view(), name="paybill_create"),
]
