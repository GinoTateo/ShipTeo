from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token


class MyAccountManager(BaseUserManager):
    def create_user(self, email, username, password=None):
        if not email:
            raise ValueError("Users must have an email address")
        if not username:
            raise ValueError("Users must have a username")
        user = self.model(
            email=self.normalize_email(email),
            username=username
        )
        user.set_password(password)
        user.save(using=self.db)
        return user

    def create_superuser(self, email, username, password):
        user = self.create_user(
            email=self.normalize_email(email),
            username=username,
            password=password,
        )
        user.is_admin = True
        user.is_staff = True
        user.is_superuser = True
        return user


def get_profile_image_filepath(self, filename):
    return f'profile_images/{self.pk}/{"profile_image.png"}'


def get_default_profile_image():
    return "TateoMerch/favicon.svg"


# Create your models here.


TITLE = (
    ('RSR', 'Route Sales Representative'),
    ('Merch', 'Merchandiser'),
    ('RM', 'Regional Manager'),
    ('DM', 'Division Manager'),
    ('WHM', 'Warehouse Manager'),
)


class Account(AbstractBaseUser):
    email = models.EmailField(verbose_name="email", max_length=60, unique=True)
    username = models.CharField(max_length=30, unique=True)
    first_name = models.CharField(max_length=30, blank=True, null=True, )
    last_name = models.CharField(max_length=30, blank=True, null=True, )
    route_number = models.IntegerField(default=0, max_length=10, blank=True, null=True)
    region_number = models.IntegerField(default=0, max_length=10, blank=True, null=True)
    date_joined = models.DateTimeField(verbose_name="date joined", auto_now_add=True)
    last_login = models.DateTimeField(verbose_name="date joined", auto_now_add=True)
    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    # profile_image = models.ImageField(max_length=255, upload_to=get_profile_image_filepath, null=True,
    #                                   default=get_default_profile_image)
    hide_email = models.BooleanField(default=True)
    title = models.CharField(choices=TITLE, blank=True, max_length=30, default='')

    objects = MyAccountManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.username

    def get_profile_image_name(self):
        return str(self.profile_image)[str(self.profile_image).index(f'profile_image/{self.pk}/'):]

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return True

    def is_merch(self):
        if self.title == "Merch":
            return True
        else:
            return False

    def is_rsr(self):
        if self.title == "RSR":
            return True
        else:
            return False

    @receiver(post_save, sender=settings.AUTH_USER_MODEL)
    def create_auth_token(sender, instance=None, created=False, **kwargs):
        if created:
            Token.objects.create(user=instance)
