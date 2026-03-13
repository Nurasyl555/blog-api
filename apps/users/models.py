from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone
import pytz


LANGUAGE_CHOICES = [
    ('en', 'English'),
    ('ru', 'Русский'),
    ('kk', 'Қазақша')
]

class UserManager(BaseUserManager):
    """
    Docstring for UserManager
    """
    def create_user(self, email: str, password: str, **extra_fields) -> 'User' :
        """"Create basic user"""
        if not email:
            raise ValueError('Email required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    def create_superuser(self, email: str, password: str, **extra_fields) -> 'User':
        """Create superuser (admin)"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, password, **extra_fields)
    

class User(AbstractBaseUser, PermissionsMixin):
    """
    Docstring for User
    """
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    avatar = models.ImageField(upload_to='avatar/', blank=True, null=True)

    language = models.CharField(
        max_length=5, 
        choices=LANGUAGE_CHOICES, 
        default='en', 
        help_text='preferred language of users'
    )
    timezone = models.CharField(
        max_length=50,
        default='UTC',
        help_text="Timezone for user(IANA timezone)"
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self) -> str:
        return self.email