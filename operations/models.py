from django.db import models
from django.urls import reverse

from rsr.models import Route
from MerchManagerV1 import settings

TYPE = (
    ('G', 'Ground'),
    ('W', 'Whole Bean'),
    ('K', 'K-Cup'),
)

BRAND = (
    ('P', 'Peets'),
    ('I', 'Intelligentsia'),
    ('S', 'Stumptown'),
)

SIZE = (
    ('18', '18oz'),
    ('10.5', '10.5oz'),
    ('10', 'K-10'),
    ('22', 'K-22'),
    ('32', 'K-32'),
    ('48', 'K-48'),
)

STATUS = (
    ('Received', 'Received'),
    ('Preparing', 'Preparing'),
    ('Shipping', 'Shipping'),
)

class Item(models.Model):
    item_brand          = models.CharField(choices=BRAND, max_length=25, default='P')
    item_type           = models.CharField(choices=TYPE, max_length=25)
    item_size           = models.CharField(choices=SIZE, max_length=25)
    item_name           = models.CharField(max_length=100)
    item_number         = models.IntegerField(default=0)
    item_date           = models.DateField(blank=True, null=True)
    cpc                 = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return self.item_name + ' ' + self.item_brand + self.item_type + self.item_size

    # def get_absolute_url(self):
    #     return reverse("product", kwargs={
    #         "pk": self.pk
    #
    #     })
    #
    # def get_add_to_cart_url(self):
    #     return reverse("add-to-cart", kwargs={
    #         "pk": self.pk
    #     })
    #
    # def get_remove_from_cart_url(self):
    #     return reverse("remove-from-cart", kwargs={
    #         "pk": self.pk
    #     })


class OrderItem(models.Model):
    user                = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    ordered             = models.BooleanField(default=False)
    item                = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity            = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} of {self.item.item_name}"

    def get_total_item_price(self):
        return self.quantity * self.item.item_size

    def get_final_quantity(self):
        if self.quantity:
            return self.quantity
        return self.quantity


class Order(models.Model):
    user                = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    route               = models.ForeignKey(Route, blank=True, default=0, on_delete=models.CASCADE)
    items               = models.ManyToManyField(OrderItem)
    start_date          = models.DateTimeField(auto_now_add=True)
    ship_date        = models.DateTimeField()
    ordered             = models.BooleanField(default=False)
    status              = models.CharField(choices=STATUS, default="Pending", max_length=25)

    def __str__(self):
        return self.user.username

    def get_total_quantity(self):
        total = 0
        for order_item in self.items.all():
            total += order_item.quantity
        return total


class InventoryItem(models.Model):
    item                = models.ForeignKey(Item, on_delete=models.CASCADE)
    item_date           = models.DateField(blank=True, null=True)
    total_quantity      = models.IntegerField(default=0)
    pallet_quantity     = models.IntegerField(default=0)
    each_quantity       = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.total_quantity} of {self.item.item_name}"


class Inventory(models.Model):
    items               = models.ManyToManyField(InventoryItem)
    date                = models.DateTimeField(auto_now_add=True)
    amount              = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.date}"


class Warehouse(models.Model):
    number              = models.IntegerField(default=000)
    manager             = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    address             = models.TextField(default="N/A")
    region              = models.IntegerField(default=0000)
    inventory           = models.ManyToManyField(Inventory, blank=True, null=True)
    routes              = models.ManyToManyField(Route, blank=True, null=True)


class OutOfStockItem(models.Model):
    item_number = models.CharField(max_length=100, unique=True, help_text="The unique item number for the OOS item")

    def __str__(self):
        return self.item_number