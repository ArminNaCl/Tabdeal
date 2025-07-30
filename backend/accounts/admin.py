from django.contrib import admin

from .models import (
    ProviderAccount,
    ProviderAccountTeamMember,
    ProviderWallet,
    PhoneNumber,
    RequestCharge,
    RequestDeposit,
)

from simple_history.admin import SimpleHistoryAdmin


class ProviderAccountTeamMemberInline(admin.TabularInline):
    model = ProviderAccountTeamMember
    extra = 1
    fields = (
        "user",
        "permission_level",
    )
    raw_id_fields = ("user",)


class ProviderWalletInline(admin.StackedInline):
    model = ProviderWallet
    can_delete = False
    max_num = 1
    fields = ("balance",)
    readonly_fields = ("balance",)


@admin.register(ProviderAccount)
class ProviderAccountAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "is_active",
        "created",
        "updated",
    )
    list_filter = ("is_active",)
    search_fields = ("name",)
    inlines = [ProviderAccountTeamMemberInline, ProviderWalletInline]
    date_hierarchy = "created"
    ordering = ("-created",)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "is_active",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created",
                    "updated",
                ),
                "classes": ("collapse",),
            },
        ),
    )
    readonly_fields = (
        "created",
        "updated",
    )

    def save_model(self, request, obj, form, change):

        super().save_model(request, obj, form, change)
        try:
            wallet_exists = obj.wallet
        except ProviderWallet.DoesNotExist:
            wallet_exists = None
        if not wallet_exists:
            ProviderWallet.objects.create(account=obj, balance=0)
            self.message_user(
                request, "Provider wallet created automatically for %s." % obj.name
            )


admin.site.register(PhoneNumber)

admin.site.register(RequestCharge)


class RequestDepositAdmin(SimpleHistoryAdmin):
    list_display = ("id", "requester", "amount", "status", "created")

    base_readonly_fields = [
        "requester",
        "user_id",
        "amount",
        "account",
    ]

    def get_readonly_fields(self, request, obj=None):
        if not obj:
            return []
        if obj and obj.is_finalized() or request.user != obj.assignee :
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
