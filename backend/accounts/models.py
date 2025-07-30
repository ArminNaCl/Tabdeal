import random

from django.db import models, transaction
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib.auth import get_user_model

from core.models import TimestampMixin

from simple_history.models import HistoricalRecords

User = get_user_model()

class ProviderAccount(TimestampMixin, models.Model):
    name = models.CharField(_("name"), max_length=100, unique=True)
    is_active = models.BooleanField(_("is_active"), default=True, db_index=True)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = _("provider account")
        verbose_name_plural = _("provider accounts")

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

class ProviderWallet(TimestampMixin, models.Model):
    account = models.OneToOneField(
        "accounts.ProviderAccount",
        on_delete=models.CASCADE,
        verbose_name=_("account"),
        related_name="wallet",
    )
    balance = models.PositiveBigIntegerField(_("balance"), default=0)

    @classmethod
    def deposit(cls, account_id: int, amount: int):
        with transaction.atomic():
            try:
                account = cls.objects.get(account_id=account_id) 
                account.balance = models.F("balance") + amount
                account.save()
            except cls.DoesNotExist():
                raise ValueError("Provider account not found.")

    def __str__(self):
        return f"{self.account.name}"

    class Meta:
        verbose_name = _("provider wallet")
        verbose_name_plural = _("provider wallets")

class RequestDeposit(TimestampMixin, models.Model):  # SupportTicket
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
        _("user_id"), help_text=_("id of requester user")
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
        blank=True
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
        self.assignee = self.select_assignee()
        super().clean()

    def save(self, *args, **kwargs):
        original_status = None
        if self.pk:
            original_request_deposit = RequestDeposit.objects.get(pk=self.pk)
            if original_request_deposit.is_finalized():
                raise ValidationError(_("Cannot modify a finalized deposit request."))
            else:
                original_status = original_request_deposit.status    

        super().save(*args, **kwargs)

        if (
            self.status == self.Status.APPROVED
            and original_status != self.Status.APPROVED
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

class PhoneNumber(TimestampMixin, models.Model):
    number = models.CharField(
        _("number"), max_length=11, validators=[RegexValidator(r"^09\d{9}")]
    )
    is_active = models.BooleanField(_("is_active"), default=True, db_index=True)

class RequestCharge(TimestampMixin, models.Model):
    phone_number = models.ForeignKey(
        "accounts.PhoneNumber",
        on_delete=models.CASCADE,
        related_name="charge_requests",
    )
    provider_account = models.ForeignKey(
        "accounts.ProviderAccount",
        on_delete=models.CASCADE,
        related_name="charge_requests",
    )
    requester = models.ForeignKey(
        "accounts.ProviderAccountTeamMember",
        verbose_name=_("requester"),
        on_delete=models.CASCADE,
        related_name="charge_requests",
    )
    user_id = models.PositiveBigIntegerField(
        _("user_id"), help_text=_("id of requester user")
    )  # requester.user.id
    amount = models.PositiveBigIntegerField("amount", default="2000")

    @classmethod
    def create_charge_safely(
        cls, phone_number_id: int, provider_account_id: int, user_id: int, amount: int
    ):
        with transaction.atomic():
            try:
                provider_wallet = ProviderWallet.objects.select_for_update().get(
                    account_id=provider_account_id
                )
                requester = ProviderAccountTeamMember.objects.get(user_id=user_id)

                phone_number = PhoneNumber.objects.get(phone_number_id=phone_number_id)

                if provider_wallet.balance < amount:
                    raise ValueError("Insufficient balance in provider account.")

                provider_wallet.balance = models.F("balance") - amount
                provider_wallet.save(update_fields=["balance"])

                request_charge = cls.objects.create(
                    phone_number=phone_number,
                    provider_account=provider_wallet.account,
                    amount=amount,
                    user_id=user_id,
                    requester=requester,
                )
                return request_charge
            except ProviderAccount.DoesNotExist:
                raise ValueError("Provider account not found.")
            except PhoneNumber.DoesNotExist:
                raise ValueError("Phone number not found.")
            except Exception as e:
                # TODO Handel Error
                raise e

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = _("request of charge")
        verbose_name_plural = _("requests of charges")
