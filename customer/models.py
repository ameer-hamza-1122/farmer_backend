import datetime
from django.db import models
from django.utils import timezone
from model_utils.models import TimeStampedModel
from rest_framework_simplejwt.tokens import SlidingToken
from phonenumber_field.modelfields import PhoneNumberField
from django.core.validators import MinValueValidator, MaxValueValidator

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


# ------------------------- News Models-------------------------

class News(models.Model):
    url = models.URLField(max_length=1000, unique=True, blank=True, null=True)
    title = models.CharField(max_length=1000, blank=True, null=True)
    image = models.URLField(max_length=1000, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    author_image = models.URLField(max_length=1000, blank=True, null=True)
    author_name = models.CharField(max_length=5000, blank=True, null=True)
    author_description = models.TextField( blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'News'
        verbose_name_plural = 'News'

    def __str__(self):
        return f"{self.id} - {self.title}"


# ------------------------- Shops Models-------------------------

class Shop(models.Model):
    url = models.URLField(max_length=1000, blank=True, null=True)
    name = models.CharField(max_length=1000, blank=True, null=True)
    image = models.URLField(max_length=1000, null=True, blank=True)
    rating = models.CharField(max_length=100, blank=True, null=True)
    location = models.CharField(max_length=1000, blank=True, null=True)
    phone_number = models.CharField(max_length=100, blank=True, null=True)
    latitude = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.id} - {self.name}"


# ------------------------- Crop-yield Models-------------------------

class YieldCalculation(models.Model):
    planting_density = models.FloatField(
        validators=[MinValueValidator(0.0)],  # Plants per square foot
        help_text="Plants per square foot"
    )
    nitrogen = models.FloatField(
        validators=[MinValueValidator(0.0)],  # Nitrogen in kg/acre
        help_text="Nitrogen applied in kg/acre"
    )
    phosphorus = models.FloatField(
        validators=[MinValueValidator(0.0)],  # Phosphorus in kg/acre
        help_text="Phosphorus applied in kg/acre"
    )
    potassium = models.FloatField(
        validators=[MinValueValidator(0.0)],  # Potassium in kg/acre
        help_text="Potassium applied in kg/acre"
    )
    disease_presence = models.BooleanField(
        default=False,  # Early Blight: Yes/No
        help_text="Presence of diseases like early blight"
    )
    pesticide_usage = models.IntegerField(
        choices=(
            (0, 'None'),
            (1, 'Regular'),
            (2, 'Intensive'),
        ),
        default=0,
        help_text="Level of pesticide usage"
    )
    leaf_health_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        default=50.0,  # 0-100 score for leaf health
        help_text="Leaf health score (0-100, based on visual assessment)"
    )
    potato_size = models.CharField(
        max_length=10,
        choices=(
            ('small', 'Small'),
            ('medium', 'Medium'),
            ('large', 'Large'),
        ),
        default='medium',
        help_text="Average potato tuber size"
    )
    field_image = models.ImageField(
        upload_to='potato_fields/',
        null=True,
        blank=True,
        help_text="Image of the potato field"
    )
    potato_image = models.ImageField(
        upload_to='potato_images/',
        null=True,
        blank=True,
        help_text="Image of harvested potatoes"
    )
    estimated_yield = models.FloatField(
        null=True,
        blank=True,
        help_text="Calculated yield in Tonnes/acre"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Yield Calculation - {self.created_at}"


# ------------------------- Leaf-Disease Models-------------------------
class LeafDisease(models.Model):
    image = models.ImageField(upload_to='leaf_diseases/', blank=True, null=True)
    Choice = models.CharField(
        max_length=100,
        choices=[
            ('Bacteria', 'Bacteria'),
            ('Fungi', 'Fungi'),
            ('Healthy', 'Healthy'),
            ('Nematode', 'Nematode'),
            ('Pest', 'Pest'),
            ('Phytopthora', 'Phytopthora'),
            ('Virus', 'Virus')
        ],
        default='Healthy'
    )
    disease_type = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.id} - {self.Choice} - {self.disease_type}"


