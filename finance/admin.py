from django.contrib import admin
from .models import PaymentTranche
admin.site.register(PaymentTranche)

from .models import ExtraService
admin.site.register(ExtraService)
