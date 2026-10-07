from django.urls import path

from .views import AnalisesView, DashboardView

app_name = "dashboard"

urlpatterns = [
    path("", DashboardView.as_view(), name="index"),
    path("analises/", AnalisesView.as_view(), name="analises"),
]
