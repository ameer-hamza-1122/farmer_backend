import codecs
from .models import News
from django.forms import ValidationError
from rest_framework import serializers, status
from django.contrib.auth.hashers import make_password
from rest_framework.exceptions import PermissionDenied
from authentication import IsCustomer, decrypt_password
from .models import Customer, ChatTicket, ChatTicketReply, YieldCalculation


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
        if customer and customer.image:
            request = self.context.get('request')
            return request.build_absolute_uri(customer.image.url) if request else f"http://localhost:8009{customer.image.url}"
        return None

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
    reply_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatTicket
        fields = ['id', 'customer', 'subject', 'description', 'created_on', 'reply_count', 'replies']

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
    
    def get_reply_count(self, obj):
        return obj.replies.count()


# --------------------- Create-bulk-news Serializer ---------------------

class NewsSerializer(serializers.ModelSerializer):
    class Meta:
        model = News
        fields = [
            'id',
            'url',
            'title',
            'image',
            'description',
            'author_image',
            'author_name',
            'author_description',
            'created_at',
            'updated_at'
        ]


# --------------------- Crop-yield-calculator Serializer ---------------------

class YieldCalculationSerializer(serializers.ModelSerializer):
    class Meta:
        model = YieldCalculation
        fields = [
            'id', 'planting_density', 'nitrogen', 'phosphorus', 'potassium',
            'disease_presence', 'pesticide_usage', 'field_image', 'estimated_yield',
            'created_at'
        ]

    def create(self, validated_data):
        # Constants from the document
        DOPT_MIN = 0.35
        DOPT_MAX = 0.40
        NOPT = 100
        POPT = 50
        KOPT = 50
        BASE_YIELD = 20  # Baseline yield in tons/acre (average from document)
        BASE_YRANGE = 10  # Assumed yield range for scaling (adjustable)

        # Extract data
        planting_density = validated_data['planting_density']
        nitrogen = validated_data['nitrogen']
        phosphorus = validated_data['phosphorus']
        potassium = validated_data['potassium']
        disease_presence = validated_data['disease_presence']
        pesticide_usage = validated_data['pesticide_usage']
        field_image = validated_data.get('field_image')

        # Step 1: Yield based on planting density
        if planting_density < DOPT_MIN:
            yield_density = BASE_YIELD - (1 - (planting_density / DOPT_MIN)) * 0.5 * BASE_YRANGE
        elif DOPT_MIN <= planting_density <= DOPT_MAX:
            yield_density = BASE_YIELD
        else:
            overcrowding_penalty = 0.08 * BASE_YRANGE
            yield_density = BASE_YIELD - overcrowding_penalty

        # Step 2: Fertilizer bonus
        n_score = min(nitrogen / NOPT, 1)
        p_score = min(phosphorus / POPT, 1)
        k_score = min(potassium / KOPT, 1)
        total_fertilizer_score = (n_score + p_score + k_score) / 3
        fertilizer_bonus = total_fertilizer_score * 1  # Max 1 ton

        # Step 3: Disease penalty
        disease_penalty = 1.0 if disease_presence else 0

        # Step 4: Pesticide bonus
        pesticide_bonus = {0: 0, 1: 0.5, 2: 1.0}[pesticide_usage]

        # Step 5: Final yield calculation
        estimated_yield = yield_density + fertilizer_bonus - disease_penalty + pesticide_bonus

        # No constraints on estimated_yield (removed YMIN, YMAX limits)

        # Create instance
        yield_calculation = YieldCalculation.objects.create(
            planting_density=planting_density,
            nitrogen=nitrogen,
            phosphorus=phosphorus,
            potassium=potassium,
            disease_presence=disease_presence,
            pesticide_usage=pesticide_usage,
            field_image=field_image,
            estimated_yield=estimated_yield
        )
        return yield_calculation

