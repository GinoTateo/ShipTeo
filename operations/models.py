from django.db import models
from MerchManagerV1 import settings

class Routes():
    route_number = models.CharField(max_length=25, blank=True, null=True)
    ship_to = models.BooleanField(default=False)
    first_name = models.CharField(max_length=30, blank=True, null=True)
    last_name = models.CharField(max_length=30, blank=True, null=True)

