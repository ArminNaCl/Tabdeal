from django.contrib import admin

from accounts.models import PhoneNumber

@admin.register(PhoneNumber)
class PhoneNumberAdmin(admin.ModelAdmin):
    list_display = ("number", "is_active", "created")
    list_filter = ("is_active",)
    search_fields = ("number",)
    date_hierarchy = "created"
    ordering = ("-created",)