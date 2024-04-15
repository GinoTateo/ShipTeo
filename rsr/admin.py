from datetime import datetime

from django.contrib import admin

from rsr.models import Store, Display, ServiceSchedule, Route, StoreListItem

admin.site.register(Store)
admin.site.register(Display)
admin.site.register(ServiceSchedule)
admin.site.register(Route)
admin.site.register(StoreListItem)
