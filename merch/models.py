from cloudinary.models import CloudinaryField
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, reverse
# from multiselectfield import MultiSelectField
from datetime import datetime, timedelta

from django.utils.timezone import now
from operations.models import Item, OrderItem
from rsr.models import Store, Route, StoreListItem


# class MerchOrderItem(models.Model):
#     user = models.ForeignKey(settings.AUTH_USER_MODEL,
#                              on_delete=models.CASCADE)
#     ordered = models.BooleanField(default=False)
#     item = models.ForeignKey(Item, on_delete=models.CASCADE)
#     quantity = models.IntegerField(default=1)
#
#     def __str__(self):
#         return f"{self.quantity} of {self.item.item_name}"


# class MerchOrder(models.Model):
#     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     store = models.ForeignKey(Store,
#                               on_delete=models.CASCADE)
#     items = models.ManyToManyField(OrderItem)
#     start_date = models.DateTimeField(auto_now_add=True)
#     ordered_date = models.DateTimeField()
#     ordered = models.BooleanField(default=False)
#
#     def __str__(self):
#         return f'{self.items.count()} skews'
#
#     def get_total_quantity(self):
#         total = 0
#         for order_item in self.items.all():
#             total += order_item.quantity
#         return total

class Merch(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user")
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="store")
    OOS = models.ManyToManyField(Item, blank=True, null=True, related_name='OOS')
    # worked_cases = models.ManyToManyField(Item, blank=True, null=True, related_name='worked_cases')
    worked_cases = models.ManyToManyField(OrderItem, blank=True, null=True)
    startDate = models.DateTimeField(auto_now_add=True)
    startBool = models.BooleanField(default=True)
    completeDate = models.DateTimeField(blank=True, null=True)
    completeBool = models.BooleanField(default=False)
    upload = CloudinaryField('/image', blank=True, null=True)
    amount = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f'{self.store} |  {self.startDate}'

    def get_num_OOS(self):
        return self.OOS.count()

    def begin(self):
        self.startBool = True
        self.startDate = now()

    def complete(self):
        self.completeDate = now()
        self.completeBool = True

    def AmountCalculator(self):
        self.amount = self.worked_cases.count() * 50


class Request(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sender')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='receiver')
    store = models.OneToOneField(Store, on_delete=models.CASCADE, default='1')
    date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True, blank=True, null=False)
    amount = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f'{self.store.name} {self.date}'

    def accept(self):
        receiver_route_list = Route.objects.get(user=self.receiver)
        if receiver_route_list:
            receiver_route_list.add_store(self.store.id)
            self.is_active = False
            self.delete()

    def decline(self):
        self.is_active = False
        self.delete()

    def cancel(self):
        self.is_active = False


class Docket(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="docket_user")
    store_list = models.ManyToManyField(StoreListItem, related_name="docket_store")
    merch_list = models.ManyToManyField(Merch, related_name="docket_merch")
    planDate = models.DateField(blank=True, null=True)
    startDate = models.DateTimeField(auto_now_add=True)
    startBool = models.BooleanField(default=True)
    completeDate = models.DateTimeField(blank=True, null=True)
    completeBool = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.user} |  {self.planDate}'

    def begin(self):
        self.startBool = True
        self.startDate = now()

    def complete(self):
        self.completeDate = now()
        self.completeBool = True
