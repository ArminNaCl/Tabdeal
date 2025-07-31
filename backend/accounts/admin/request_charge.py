from django.contrib import admin

from accounts.models import RequestCharge

@admin.register(RequestCharge)
class RequestChargeAdmin(admin.ModelAdmin):
    list_display = ("provider_account", "phone_number", "requester","amount" )
    list_filter = ("provider_account",)
    search_fields = ("phone_number",)
    date_hierarchy = "created"
    ordering = ("-created",)