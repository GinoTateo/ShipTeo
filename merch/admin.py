import datetime
from django.utils.datetime_safe import datetime
from django.contrib import admin
from .models import Merch, Request, Docket

#
admin.site.register(Merch)
admin.site.register(Request)
admin.site.register(Docket)
