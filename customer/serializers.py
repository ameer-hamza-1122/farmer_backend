import codecs
from .models import Customer, ChatTicket, ChatTicketReply
from django.forms import ValidationError
from rest_framework import serializers, status
from django.contrib.auth.hashers import make_password
from rest_framework.exceptions import PermissionDenied
from authentication import IsCustomer, decrypt_password


# --------------------- Custom Validation Error Class ---------------------

class CustomValidationError(PermissionDenied):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid input value"
    default_code = 'invalid'

    def __init__(self, detail, status_code=None):
        self.detail = detail if detail else self.default_detail
        if status_code is not None:
            self.status_code = status_code

# --------------------- CUSTOMER CRUD Serializer ---------------------

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name', 'username', 'email', 'password', 'phone', 'address', 'image', 'created_on']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def update(self, instance, validated_data):
        from authentication import encrypt_password
        # Check if password is part of the validated data
        if 'password' in validated_data:
            password = validated_data['password']
            if len(password) < 8:
                raise CustomValidationError(
                    detail='Password must be at least 8 characters long.',
                    status_code=status.HTTP_411_LENGTH_REQUIRED
                )
            encrypted_password, key = encrypt_password(password)
            validated_data['password'] = encrypted_password.decode('utf-8')
            validated_data['password_key'] = key.decode('utf-8')

        return super().update(instance, validated_data)
    
# --------------------- CUSTOMER Login Serializer ---------------------

class RegisterCustomerSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    encryption_key = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Customer
        fields = ['id', 'name', 'username', 'email', 'password', 'phone', 'address', 'image', 'created_on', 'encryption_key']
        extra_kwargs = {
            'password': {'write_only': True},
            'created_on': {'read_only': True},
        }

    def create(self, validated_data):
        from authentication import encrypt_password
        # Encrypt the password and store the encryption key securely
        password, key = encrypt_password(validated_data['password'])    
        validated_data['password'] = password.decode('UTF-8') if isinstance(password, bytes) else password
        validated_data['password_key'] = key.decode('UTF-8') if isinstance(key, bytes) else key
        return super().create(validated_data)

    def validate_password(self, value):
        # Ensure password meets any custom requirements
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        return value


class CustomerLoginSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField(read_only=True)
    name = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    phone = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    created_on = serializers.SerializerMethodField()
    jwt_token = serializers.SerializerMethodField()

    def get_id(self, obj):
        customer = Customer.objects.filter(email=obj['email']).last()
        return customer.id if customer else ''

    def get_name(self, obj):
        customer = Customer.objects.filter(email=obj['email']).last()
        return customer.name.capitalize() if customer else ''

    def get_username(self, obj):
        customer = Customer.objects.filter(email=obj['email']).last()
        return customer.username.capitalize() if customer else ''

    def get_phone(self, obj):
        customer = Customer.objects.filter(email=obj['email']).last()
        return str(customer.phone) if customer else ''

    def get_address(self, obj):
        customer = Customer.objects.filter(email=obj['email']).last()
        return customer.address if customer else ''

    def get_image(self, obj):
        customer = Customer.objects.filter(email=obj['email']).last()
        return customer.image.url if customer and customer.image else None

    def get_created_on(self, obj):
        customer = Customer.objects.filter(email=obj['email']).last()
        return customer.created_on if customer else None

    def validate(self, data):
        customers = Customer.objects.filter(email=data['email'])
        if customers.exists():
            customer = customers.last()
            if decrypt_password(codecs.encode(customer.password, 'UTF-8'),
                                codecs.encode(customer.password_key, 'UTF-8')) == data['password']:
            # if customer.password == data['password']:
                return data
            else:
                raise CustomValidationError(
                    detail='Password is incorrect. Please proceed with current credentials.',
                    status_code=status.HTTP_409_CONFLICT
                )
        else:
            raise CustomValidationError(
                detail='There is no account attached with this email.',
                status_code=status.HTTP_409_CONFLICT
            )

    def get_jwt_token(self, data):
        """
        Read only field to send jwt token.
        """
        user = Customer.objects.get(email=data['email'])
        token = Customer.get_jwt_token(user)
        return str(token)

    def create(self, validated_data):
        return validated_data

# --------------------- CUSTOMER Forgot-password Serializer ---------------------

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordWithOTPSerializer(serializers.Serializer):
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True)


# --------------------- Community-chat Serializer ---------------------

class ChatTicketReplySerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(many=False, read_only=True)
    class Meta:
        model = ChatTicketReply
        fields = ['id', 'ticket', 'customer', 'message', 'created_on']

   
class ChatTicketSerializer(serializers.ModelSerializer):
    replies = ChatTicketReplySerializer(many=True, read_only=True)
    customer = CustomerSerializer(many=False, read_only=True)

    class Meta:
        model = ChatTicket
        fields = ['id', 'customer', 'subject', 'description', 'created_on', 'replies']

    def validate(self, data):
        customer = self.context['request'].user

        if ChatTicket.objects.filter(
            customer=customer, 
            subject=data.get('subject'), 
            description=data.get('description')
        ).exists():
            raise CustomValidationError(
                detail='You have already created a chat ticket with the same subject and description.',
                status_code=status.HTTP_409_CONFLICT
            )

        return data
