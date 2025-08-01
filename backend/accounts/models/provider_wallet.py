from django.db import models, transaction
from django.utils.translation import gettext_lazy as _


from core.models import TimestampMixin


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
                print(account_id)
                account = cls.objects.get(account_id=account_id)
                account.balance = models.F("balance") + amount
                account.save()
            except ProviderWallet.DoesNotExist:
                raise ValueError("Provider account not found.")

    def __str__(self):
        return f"{self.account.name}"

    class Meta:
        verbose_name = _("provider wallet")
        verbose_name_plural = _("provider wallets")
