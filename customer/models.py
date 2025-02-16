import datetime
from django.db import models
from django.utils import timezone
from model_utils.models import TimeStampedModel
from rest_framework_simplejwt.tokens import SlidingToken
from phonenumber_field.modelfields import PhoneNumberField

# Create your models here.

# ------------------------- Customer Models-------------------------
class Customer(TimeStampedModel):
    name = models.CharField(max_length=100)
    username = models.CharField(max_length=100, unique=True, null=False, blank=False)
    email = models.EmailField(unique=True, null=False, blank=False)
    password = models.CharField(max_length=100, blank=False, null=False)
    password_key = models.CharField(max_length=100, blank=False, null=False)
    phone = PhoneNumberField(unique=True, region='PK', blank=False, null=False)
    address = models.TextField( blank=True, null=True)
    image = models.ImageField(upload_to='customer/', blank=True, null=True)
    created_on = models.DateTimeField(auto_now_add=True)
    otp = models.CharField(max_length=6, blank=True, null=True)

    def set_password(self, raw_password):
        """Hashes the password and saves it securely using encryption."""
        from authentication import encrypt_password
        password, key = encrypt_password(raw_password)
        self.password = password.decode('UTF-8')
        self.password_key = key.decode('UTF-8') 

    class Meta:
        ordering = ('-created_on',)

    def __str__(self):
        return f"{self.id} - {self.username}"
    
    @classmethod
    def get_jwt_token(cls, user):
        token = SlidingToken.for_user(user)
        token['user_id'] = user.id
        token['customer'] = {
            'id': user.id,
            'email': user.email,
        }
        return token


class OneTimePassword(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    otp = models.CharField(max_length=6, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def is_valid(self):
        validity_duration = timezone.timedelta(minutes=5)
        return timezone.now() - self.created_at <= validity_duration


# ------------------------- Community-Chat Models-------------------------

class ChatTicket(TimeStampedModel):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="tickets",
    )
    subject = models.CharField(max_length=255)
    description = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f"{self.id} - {self.subject} - {self.customer}"


class ChatTicketReply(TimeStampedModel):
    ticket = models.ForeignKey(
        ChatTicket,
        on_delete=models.CASCADE,
        related_name="replies",
        null=True,
        blank=True,
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="ticket_replies",
        null=True,
        blank=True,
        default=True,
    )
    message = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f"{self.id} - Reply by {self.customer}"

