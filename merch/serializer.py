from .models import Merch
from rest_framework import serializers

class MerchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Merch
        fields = ['id', 'user', 'store', 'OOS', 'case_count', 'date', 'upload']