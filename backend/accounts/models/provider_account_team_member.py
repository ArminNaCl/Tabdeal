import random

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from core.models import TimestampMixin



class ProviderAccountTeamMember(TimestampMixin, models.Model):
    class PermissionLevel(models.TextChoices):
        ADMIN = "admin", _("admin")  # it can requestCharge and requestDeposit
        STAFF = "staff", _("staff")  # It can only requestCharge
        USER = "user", _("user")  # It can only see the Info

    account = models.ForeignKey(
        "accounts.ProviderAccount",
        on_delete=models.CASCADE,
        related_name="team_members",
        verbose_name=_("account"),
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="team",
        verbose_name=_("user"),
    )
    permission_level = models.CharField(
        _("permission level"),
        max_length=10,
        choices=PermissionLevel.choices,
        default=PermissionLevel.USER,
    )

    def __str__(self):
        return f"{self.account.name} - {self.user.username} ({self.permission_level})"

    class Meta:
        verbose_name = _("provider account team member")
        verbose_name_plural = _("provider accounts team members")