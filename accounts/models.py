from django.contrib.auth.models import AbstractUser
from django.db import models
from cloudinary.models import CloudinaryField


class CustomUser(AbstractUser):

    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('customer', 'Customer'),
    )
    username = models.CharField(
        max_length=150,
        unique=True,
    )
    email= models.EmailField(unique= True,)

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='customer'
    )
    is_email_verified= models.BooleanField(default=False)
 

    def is_admin_user(self):
        return self.role == 'admin'

    def save(self, *args, **kwargs):
        if self.is_staff:
            self.role = 'admin'
            self.is_email_verified= True
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.username} ({self.role})'


class Profile(models.Model):

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    ###3 Fixed quotes
    avatar = CloudinaryField(
        'avatar',
        null=True,
        blank=True,
        folder='avatars/',
    )

    #### Auto-generated avatar URL from UI Avatars
    avatar_url = models.URLField(
        null=True,
        blank=True
    )

    phone = models.CharField(max_length=20, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def _generate_avatar_url(self):
        name = self.user.get_full_name() or self.user.username
        initials = '+'.join(name.split()[:2])
        return (
            f'https://ui-avatars.com/api/'
            f'?name={initials}'
            f'&size=200'
            f'&background=60BB46'
            f'&color=ffffff'
            f'&bold=true'
            f'&rounded=true'
        )

    def save(self, *args, **kwargs):
        if not self.avatar and not self.avatar_url:
            self.avatar_url = self._generate_avatar_url()
        super().save(*args, **kwargs)

    def get_avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return self.avatar_url or self._generate_avatar_url()

    def __str__(self):
        return f'{self.user.username} profile'