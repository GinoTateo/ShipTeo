from .models import Item
import django_filters
# from django_filters.filters import RangeFilter


# Creating product filters
class ItemFilter(django_filters.FilterSet):
    # name = django_filters.CharFilter(lookup_expr='icontains')
    # price = RangeFilter()

    class Meta:
        model = Item
        fields = ['item_type', 'item_size', 'item_brand']
