from django.db import models
from django.utils.translation import ugettext_lazy as _

class Consumer(models.Model):
    """
        OAuth consumer class.  Authentication credentials go in here.
    """

    class Meta:
        verbose_name = _("Consumer")
        verbose_name_plural = _("Consumers")

    consumer_key = models.CharField(_("Consumer Key"), max_length=64)
    consumer_sec = models.CharField(_("Consumer Secret"), max_length=64)
    access_key   = models.CharField(_("Access Key"), max_length=64)
    access_sec   = models.CharField(_("Access Secret"), max_length=64)


    @property
    def secret(self):
        return self.consumer_sec


    @property
    def key(self):
        return self.consumer_key



class Nonce(models.Model):
    """

        The OAuth spec requires the testing of a nonce in the URL.  To do
        this, create an instance of this model, setting \a key to the nonce
        value and attempt to save it.  If it fails throwing an IntegrityError,
        you know it failed.

        NOTE: This process works under the assumption that the maintenence
        NOTE: scripts delete old nonces every once in a while as this will
        NOTE: (a) improve performance, and (b) reduce the likelyhood of a
        NOTE: false positive.

    """
    key  = models.BigIntegerField(unique=True)
    time = models.DateTimeField(auto_now_add=True)

