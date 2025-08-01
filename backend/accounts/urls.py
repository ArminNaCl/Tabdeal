from django.urls import path

from accounts.api import request_charge_api_view, request_deposit_detail, request_deposit_list_create

urlpatterns = [
    path("request_charge/", request_charge_api_view, name="request_charge"),
    path("request_deposit/", request_deposit_list_create, name="request_deposit"),
    path("request_deposit/<int:pk>/", request_deposit_detail, name="request_deposit_detail"),
    
]