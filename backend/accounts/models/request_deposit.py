import random

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib.auth import get_user_model

from core.models import TimestampMixin
from accounts.models import ProviderWallet, ProviderAccountTeamMember

from simple_history.models import HistoricalRecords

User = get_user_model()


# Name Can be Support Ticket too
class RequestDeposit(TimestampMixin, models.Model):
    class Status(models.TextChoices):
        OPEN = "open", _("open")
        APPROVED = "approved", _("approved")
        REJECTED = "rejected", _("rejected")

    requester = models.ForeignKey(
        "accounts.ProviderAccountTeamMember",
        verbose_name=_("requester"),
        on_delete=models.CASCADE,
        related_name="deposit_requests",
    )
    user_id = models.PositiveBigIntegerField(
        _("user_id"), help_text=_("id of requester user"), blank=True, null=True
    )  # requester.user.id

    amount = models.PositiveBigIntegerField("amount")
    account = models.ForeignKey(
        "accounts.ProviderAccount", on_delete=models.CASCADE, verbose_name=_("account")
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("assignee"),
        on_delete=models.CASCADE,
        related_name="deposit_requests",
        blank=True,
    )
    comment = models.TextField(
        _("comment"), blank=True, null=True
    )  # NOTE Since we have django-simple-history we dont need another model for this
    status = models.CharField(
        _("status"), max_length=20, default=Status.OPEN, choices=Status.choices
    )
    history = HistoricalRecords()

    def is_finalized(self):
        return self.status in [self.Status.APPROVED, self.Status.REJECTED]

    def select_assignee(self):
        return random.choice(User.objects.filter(is_staff=True))

    def clean(self):
        if self.pk:
            original_request_deposit = RequestDeposit.objects.get(pk=self.pk)
            if original_request_deposit.is_finalized():
                raise ValidationError(
                    _("Cannot change the status of a finalized deposit request.")
                )

    def save(self, *args, **kwargs):
        if self.pk:
            is_new = False
            original_request_deposit = RequestDeposit.objects.get(pk=self.pk)
            if original_request_deposit.is_finalized():
                raise ValidationError(_("Cannot modify a finalized deposit request."))
            else:
                original_status = original_request_deposit.status
        else:
            original_status = None
            is_new = True
            if (
                self.requester.account != self.account
                or self.requester.permission_level
                != ProviderAccountTeamMember.PermissionLevel.ADMIN
            ):
                raise PermissionError(
                    "The Requester user does not have permission to this action"
                )
            if not self.assignee_id:
                self.assignee = self.select_assignee()
            if not self.user_id:
                self.user_id = self.requester.user.id

        super().save(*args, **kwargs)

        if (
            self.status == self.Status.APPROVED
            and original_status != self.Status.APPROVED
            and not is_new
        ):
            ProviderWallet.deposit(account_id=self.account.id, amount=self.amount)

    def delete(self, *args, **kwargs):
        if self.is_finalized():
            raise ValidationError(_("Cannot delete a finalized deposit request."))
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.id}"

    class Meta:
        verbose_name = _("request of deposit")
        verbose_name_plural = _("requests of deposit")
