from django.db import models
from django.utils.translation import gettext_lazy as _


class TimestampMixin(models.Model):
    created = models.DateTimeField(_("create timestamp"), auto_now_add=True)
    updated = models.DateTimeField(_("update timestamp"), auto_now=True)

    class Meta:
        abstract = True
