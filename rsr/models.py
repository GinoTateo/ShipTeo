from datetime import datetime, timedelta

from django.db import models
from django.urls import reverse

from MerchManagerV1 import settings
from account.models import Account

DISPLAY_TYPE = (
    ('Shipper', 'Shipper'),
    ('Wire rack', 'Wire rack'),
    ('Hanging rack', 'Hanging rack'),
    ('End cap', 'End cap'),
    ('Rolling rack', 'Rolling rack'),
)

DISPLAY_LOCATION = (
    ('BOH', 'Back of house'),
    ('FOH', 'Front of house'),
    ('Aisle', 'Aisle'),
    ('Bakery', 'Bakery'),
    ('Deli', 'Deli'),
    ('Pharmacy', 'Pharmacy'),
    ('Check-stand', 'Check-stand'),
)

WEEKDAYS = (
    ('Monday', 'Monday'),
    ('Tuesday', 'Tuesday'),
    ('Wednesday', 'Wednesday'),
    ('Thursday', 'Thursday'),
    ('Friday', 'Friday'),
    ('Saturday', 'Saturday'),
    ('Sunday', 'Sunday'),
)

STORE = (
    ('Safeway', 'Safeway'),
    ('Target', 'Target'),
    ('Lucky', 'Lucky'),
    ('FoodMaxx', 'FoodMaxx'),
    ('SaveMart', 'SaveMart'),
    ('Lunardis', 'Lunardis'),
    ('Nob Hill', 'Nob Hill'),
    ('Wholefoods', 'Wholefoods'),
    ('BerkeleyBowl', 'BerkeleyBowl'),
    ('Pak n Save', 'Pak n Save'),
    ('Village Market', 'Village Market'),
)

RECEIVE_TYPE = (
    ('DEX', 'DEX'),
    ('SCAN', 'SCAN'),
    ('SIGN', 'SIGN'),
)


class Display(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    active = models.BooleanField(default=False)
    location = models.CharField(default="End cap", choices=DISPLAY_LOCATION, max_length=25)
    type = models.CharField(default="Shipper", choices=DISPLAY_TYPE, max_length=25)
    description = models.CharField(default="", max_length=140)

    def __str__(self):
        return f"{self.type} at {self.location}"


def default_start_time():
    now = datetime.now()
    start = now.replace(hour=22, minute=0, second=0, microsecond=0)
    return start if start > now else start + timedelta(days=1)


class Store(models.Model):
    name = models.CharField(default="Safeway", choices=STORE, max_length=25)
    number = models.IntegerField(default="", max_length=100, blank=True, null=True)
    City = models.CharField(default="", max_length=25)
    # Service_days = models.ForeignKey('ServiceDay', on_delete=models.CASCADE, default="Monday")
    RSRrt = models.IntegerField(default="", max_length=100)
    Area = models.CharField(default="", max_length=25)
    receiver_name = models.CharField(default="", max_length=25)
    receiver_open = models.TimeField(default=default_start_time)
    receiver_close = models.TimeField(default=default_start_time)
    receive_type = models.CharField(default="DEX", choices=RECEIVE_TYPE, max_length=25)
    weekly_average = models.IntegerField(default=0, max_length=100)
    Address = models.CharField(default="", max_length=50)
    BS_Location = models.CharField(default="", max_length=50)
    displays = models.ManyToManyField(Display, blank=True, null=True, related_name='Display')
    merchandiser = models.ForeignKey(Account, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return f'{self.name} {self.number}'


class StoreListItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    complete = models.BooleanField(default=False)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    position = models.IntegerField(default=0)

    def __str__(self):
        return f'{self.store} {self.position}'


class ServiceSchedule(models.Model):
    day = models.CharField(default="Monday", choices=WEEKDAYS, max_length=25)
    store = models.OneToOneField(Store, on_delete=models.CASCADE)
    time_frame = models.IntegerField
    frequency = models.IntegerField(default=0, max_length=100, blank=True, null=True)

    def __str__(self):
        return f'{self.day} {self.time_frame}'


class Route(models.Model):
    number = models.IntegerField(default='0', blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True)
    region = models.IntegerField(default='4208', blank=True)
    store = models.ManyToManyField(Store, blank=True)


    def __str__(self):
        return f'{self.number}'

    def add_store(self, store_id):
        store_request = Store.objects.get(id=store_id)
        if not store_request in self.store.all():
            self.store.add(store_request.id)
