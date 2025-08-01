from django.contrib.auth import PermissionDenied
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from core.models import TimestampMixin
from accounts.models import ProviderWallet, ProviderAccountTeamMember, PhoneNumber


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
                if not amount or amount <= 0:
                    raise ValueError("Charge amount must be positive.")
                provider_wallet = ProviderWallet.objects.select_for_update().get(
                    account_id=provider_account_id
                )
                requester = ProviderAccountTeamMember.objects.get(user_id=user_id)

                phone_number = PhoneNumber.objects.get(id=phone_number_id)

                if provider_wallet.balance < amount:
                    raise ValueError("Insufficient balance in provider account.")
                if requester.permission_level not in [
                    ProviderAccountTeamMember.PermissionLevel.ADMIN,
                    ProviderAccountTeamMember.PermissionLevel.STAFF,
                ]:
                    raise PermissionError(
                        "The Requester user does not have permission to this action"
                    )

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
            except ProviderWallet.DoesNotExist:
                raise ValueError("Provider wallet not found.")
            except PhoneNumber.DoesNotExist:
                raise ValueError("Phone number not found.")
            except ProviderAccountTeamMember.DoesNotExist:
                raise ValueError("Requester not found.")
            except Exception as e:
                # TODO Handel Error
                raise e

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = _("request of charge")
        verbose_name_plural = _("requests of charges")
