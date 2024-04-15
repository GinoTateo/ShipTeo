from django.contrib.auth import authenticate

from rest_framework import serializers
from account.models import Account
from merch.models import Merch, Docket, Request
from rsr.models import Store, Route


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(
        label="Username",
        write_only=True
    )
    password = serializers.CharField(
        label="Password",
        # This will be used when the DRF browsable API is enabled
        style={'input_type': 'password'},
        trim_whitespace=False,
        write_only=True
    )

    def validate(self, attrs):
        # Take username and password from request
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            # Try to authenticate the user using Django auth framework.
            user = authenticate(request=self.context.get('request'),
                                username=username, password=password)
            if not user:
                # If we don't have a regular user, raise a ValidationError
                msg = 'Access denied: wrong username or password.'
                raise serializers.ValidationError(msg, code='authorization')
        else:
            msg = 'Both "username" and "password" are required.'
            raise serializers.ValidationError(msg, code='authorization')
        # We have a valid user, put it in the serializer's validated_data.
        # It will be used in the view.
        attrs['user'] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = [
            'username',
            'email',
            'first_name',
            'last_name',
        ]


class MerchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Merch
        fields = [
            'user',
            'store',
            'OOS',
            'worked_cases',
            'date',
        ]


class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = [
            'name',
            'number',
            'City',
            'RSRrt',
            'Area',
            'receiver_name',
            'receiver_open',
            'receiver_close',
            'receive_type',
            'weekly_average',
            'Address',
            'BS_Location',
            'displays',
            'merchandiser'
        ]

class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = [
            'number',
            'user',
            'region',
            'store'
        ]

class DocketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Docket
        fields = [
            'user',
            'store_list',
            'date',
            'completed'
        ]


class RequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Request
        fields = [
            'sender',
            'receiver',
            'store',
            'date',
            'is_active'
        ]
