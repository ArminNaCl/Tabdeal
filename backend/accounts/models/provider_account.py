from django.db import models
from django.utils.translation import gettext_lazy as _


from core.models import TimestampMixin


class ProviderAccount(TimestampMixin, models.Model):
    name = models.CharField(_("name"), max_length=100, unique=True)
    is_active = models.BooleanField(_("is_active"), default=True, db_index=True)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = _("provider account")
        verbose_name_plural = _("provider accounts")
