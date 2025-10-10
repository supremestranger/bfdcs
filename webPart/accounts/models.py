from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('admin', 'Administrator'),
        ('ordinary', 'Ordinary User'),
    )
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='ordinary')
    email = models.EmailField(unique=True)

    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"


class AdminProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_profile')
    department = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    permissions_level = models.IntegerField(default=1, choices=[
        (1, 'Базовый'),
        (2, 'Расширенный'),
        (3, 'Полный доступ')
    ])
    access_code = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Admin Profile: {self.user.username}"


class OrdinaryUserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='ordinary_profile')
    bio = models.TextField(blank=True, max_length=500)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    birth_date = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=100, blank=True)
    subscription_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"User Profile: {self.user.username}"


# Автоматическое создание профиля при создании пользователя
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.user_type == 'admin':
            AdminProfile.objects.create(user=instance)
        else:
            OrdinaryUserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if instance.user_type == 'admin':
        if not hasattr(instance, 'admin_profile'):
            AdminProfile.objects.create(user=instance)
        instance.admin_profile.save()
    else:
        if not hasattr(instance, 'ordinary_profile'):
            OrdinaryUserProfile.objects.create(user=instance)
        instance.ordinary_profile.save()