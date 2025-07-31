from django.contrib import admin

from simple_history.admin import SimpleHistoryAdmin

from accounts.models import RequestDeposit


class RequestDepositAdmin(SimpleHistoryAdmin):
    list_display = ("id", "requester", "amount", "status", "created")

    base_readonly_fields = [
        "requester",
        "user_id",
        "amount",
        "account",
    ]
    
    list_filter = ("status","assignee","account",) 

    date_hierarchy = "created"
    ordering = ("-created",)

    def get_readonly_fields(self, request, obj=None):
        if not obj:
            return []
        if obj and obj.is_finalized() or request.user != obj.assignee:
            return [field.name for field in self.model._meta.fields]

        return self.base_readonly_fields

    def has_change_permission(self, request, obj=None):
        if obj and not obj.is_finalized():
            return request.user.is_superuser or request.user != obj.assignee
        return False

    def has_delete_permission(self, request, obj=None):
        if obj and not obj.is_finalized():
            return request.user.is_superuser or request.user != obj.assignee
        return False


admin.site.register(RequestDeposit, RequestDepositAdmin)
