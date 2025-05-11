import os
import re
import json
import time
from mistralai import Mistral
from django.conf import settings
from customer import serializers
from django.db.models import Func
from rest_framework import status
from smtplib import SMTPException
from mistralai.models import SDKError
from django.core.mail import send_mail
from rest_framework.views import APIView
from django.core.mail import BadHeaderError
from rest_framework.response import Response
from rest_framework import viewsets, generics
from rest_framework.permissions import AllowAny
from django.utils.crypto import get_random_string
from django.utils.decorators import method_decorator
from rest_framework.permissions import IsAuthenticated
from authentication import CustomJWTAuthentication, IsCustomer
from rest_framework.exceptions import NotFound, PermissionDenied
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from .models import Customer, OneTimePassword, ChatTicket, ChatTicketReply, News
from rest_framework.generics import CreateAPIView, RetrieveAPIView, ListAPIView
from rest_framework.decorators import action, permission_classes, authentication_classes
from .serializers import CustomerLoginSerializer, CustomerSerializer, RegisterCustomerSerializer,ForgotPasswordSerializer, ResetPasswordWithOTPSerializer, NewsSerializer

# --------------------- CUSTOMER GET, UPDATE, DELETE ---------------------

class CustomerViewSet(viewsets.ModelViewSet):
    authentication_classes = (CustomJWTAuthentication,)
    permission_classes = (IsCustomer,)
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer

    # This method returns all the users existed in database
    def retrieve(self, request, pk=None):
        customer = self.get_object()
        serializer = self.get_serializer(customer)
        return Response(serializer.data)

    # Updates the requested user's data
    def update(self, request, pk=None):
        customer = self.get_object()
        serializer = self.get_serializer(customer, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Delete the requested user
    def destroy(self, request, *args, **kwargs):
        customer = request.user
        try:
            customer.delete()
        except:
            raise 
        return Response(
            {"message": "Customer deleted successfully!"},
            status=status.HTTP_204_NO_CONTENT
        )

# --------------------- CUSTOMER Register, Login ---------------------

class RegisterCustomerAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = RegisterCustomerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomerLoginAPIView(CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = serializers.CustomerLoginSerializer

    def post(self, request, *args, **kwargs):
        login_serializer = self.get_serializer_class()
        login_serializer(data=request.data).is_valid(raise_exception=True)
        return self.create(request, *args, **kwargs)

# --------------------- CUSTOMER Forgot-password APIView ---------------------

class ForgotPasswordAPIView(APIView):
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            try:
                customer = Customer.objects.filter(email=email).first()
                if not customer:
                    return Response({"detail": f'Customer with {email} does not exist.'}, status=status.HTTP_404_NOT_FOUND)
                otp = get_random_string(length=6, allowed_chars='0123456789')
                OneTimePassword.objects.create(customer=customer, otp=otp)

                try:
                    send_mail(
                        subject='Password Reset OTP',
                        message=f'Your OTP for password reset is: {otp}',
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[email],
                    )
                except BadHeaderError:
                    return Response({"error": "Invalid header found."}, status=status.HTTP_400_BAD_REQUEST)
                except SMTPException as e:
                    return Response({"error": f"Email sending failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                return Response({"message": "OTP sent to your email for password reset."}, status=status.HTTP_200_OK)
            except Customer.DoesNotExist:
                return Response({"error": "User with the provided email does not exist."}, status=status.HTTP_404_NOT_FOUND)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class ResetPasswordWithOTPAPIView(APIView):
    def post(self, request):
        serializer = ResetPasswordWithOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp = serializer.validated_data['otp']
        new_password = serializer.validated_data['new_password']

        try:
            otp_obj = OneTimePassword.objects.get(otp=otp)
            customer = otp_obj.customer
            customer.set_password(new_password)
            customer.save()
            otp_obj.delete()

            return Response({"message": "Password reset successful."}, status=status.HTTP_200_OK)
        except OneTimePassword.DoesNotExist:
            return Response({"detail": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)


# --------------------- Community-chat APIView ---------------------

class TicketListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = serializers.ChatTicketSerializer
    authentication_classes = (CustomJWTAuthentication,)
    permission_classes = (IsCustomer,)

    def get_queryset(self):
        customer = self.request.user
        return ChatTicket.objects.filter(customer=customer)

    def perform_create(self, serializer):
        customer = self.request.user
        serializer.save(customer=customer)


class ListAllChatTickets(APIView):
    authentication_classes = (CustomJWTAuthentication,)
    permission_classes = (IsCustomer,)

    def get(self, request):
        chat_tickets = ChatTicket.objects.all().order_by('-created_on')
        serializer = serializers.ChatTicketSerializer(chat_tickets, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TicketDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = serializers.ChatTicketSerializer
    authentication_classes = (CustomJWTAuthentication,)
    permission_classes = (IsCustomer,)
    queryset = ChatTicket.objects.all()


class TicketReplyListAPIView(generics.ListCreateAPIView):
    authentication_classes = (CustomJWTAuthentication,)
    permission_classes = (IsCustomer,)
    serializer_class = serializers.ChatTicketReplySerializer

    def get_queryset(self):
        ticket_id = self.kwargs['ticket_id']
        return ChatTicketReply.objects.filter(ticket_id=ticket_id)
  
    
class TicketReplyCreateAPIView(generics.CreateAPIView):
    serializer_class = serializers.ChatTicketReplySerializer
    authentication_classes = (CustomJWTAuthentication,)
    permission_classes = (IsCustomer,)

    def perform_create(self, serializer):
        user = self.request.user
        ticket_id = self.kwargs['ticket_id']
        ticket = ChatTicket.objects.get(id=ticket_id)
        serializer.save(ticket=ticket, customer=user)


# --------------------- Create-bulk-news APIView ---------------------

class BulkNewsCreateAPIView(APIView):
    authentication_classes = (CustomJWTAuthentication,)
    permission_classes = (IsCustomer,)

    def post(self, request):
        # Path to JSON file in the project's base directory
        json_file_path = os.path.join(settings.BASE_DIR, 'article_details.json')
        
        try:
            # Read the JSON file
            with open(json_file_path, 'r') as file:
                news_data = json.load(file)
                # Map JSON field names to model field names
                mapped_data = []
                for item in news_data:
                    # Sanitize image and author_image fields
                    image = item.get('Image')
                    author_image = item.get('Author Image')
                    
                    # Convert to None if null, empty, or not a valid URL
                    if image is None or image == '' or not isinstance(image, str) or not re.match(r'^https?://', image):
                        image = None
                    if author_image is None or author_image == '' or not isinstance(author_image, str) or not re.match(r'^https?://', author_image):
                        author_image = None

                    mapped_item = {
                        'url': item.get('URL', ''),
                        'title': item.get('Title', ''),
                        'image': image,
                        'description': item.get('Description', ''),
                        'author_image': author_image,
                        'author_name': item.get('Author Name', ''),
                        'author_description': item.get('Author Description', '')
                    }
                    mapped_data.append(mapped_item)

                serializer = NewsSerializer(data=mapped_data, many=True)
                if serializer.is_valid():
                    news_instances = [
                        News(**item) for item in serializer.validated_data
                    ]
                    
                    News.objects.bulk_create(news_instances)
                    
                    return Response({
                        "message": f"Successfully created {len(news_instances)} news items",
                        "count": len(news_instances)
                    }, status=status.HTTP_201_CREATED)
                else:
                    print("Serializer errors:", serializer.errors)  # Debug: Check validation errors
                    return Response({
                        "error": "Invalid data",
                        "details": serializer.errors
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
        except FileNotFoundError:
            return Response({"error": "JSON file not found in project directory"}, status=status.HTTP_404_NOT_FOUND)
        except json.JSONDecodeError:
            return Response({"error": "Invalid JSON format in file"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Error processing news items: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RandomNewsAPIView(APIView):
    authentication_classes = (CustomJWTAuthentication,)
    permission_classes = (IsCustomer,)
    
    def get(self, request):
        try:
            news_items = News.objects.all().order_by(Func(function='RANDOM'))
            serializer = NewsSerializer(news_items, many=True)
            return Response({
                "message": "Successfully retrieved random news items",
                "count": len(serializer.data),
                "data": serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "error": f"Error retrieving news items: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --------------------- GROK API-Key APIView ---------------------

class AIChatView(APIView):
    authentication_classes = (CustomJWTAuthentication,)
    permission_classes = (IsCustomer,)
    
    def post(self, request):
        # Extract acres from request body
        acres = request.data.get('acres')
        disease = request.data.get('disease')
        # Optional: Validate disease input
        if disease and not isinstance(disease, str):
            return Response(
                {"error": "Invalid input: Disease must be a string"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate input
        if not acres:
            return Response(
                {"error": "Number of acres is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            acres = float(acres)
            if acres <= 0:
                raise ValueError("Acres must be a positive number")
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid input: Acres must be a positive number"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Initialize Mistral client
        api_key = settings.MISTRAL_API_KEY
        client = Mistral(api_key=api_key)

        def make_request_with_retry(client, model, messages, max_retries=3):
            for attempt in range(max_retries):
                try:
                    response = client.chat.complete(
                        model=model,
                        messages=messages
                    )
                    return response
                except SDKError as e:
                    if "429" in str(e):
                        wait_time = 2 ** attempt  # Exponential backoff
                        print(f"Rate limit hit, waiting {wait_time} seconds...")
                        time.sleep(wait_time)
                    else:
                        raise e
            raise Exception("Max retries exceeded")

        # Craft prompt to restrict AI to potato crop and fertilizer information only
        prompt = (
            f"A farmer has {acres} acres of potato crops. Provide detailed recommendations for the amount of fertilizer, "
            f"{f' affected by {disease}' if disease else ''}. "
            f"Provide detailed recommendations for the amount of fertilizer, "
            f"macro-fertilizer (nitrogen, phosphorus, potassium), and water required for optimal potato crop growth. "
            f"Include specific quantities (e.g., kg per acre or liters per acre) and any relevant application schedules. "
            f"Focus only on potato crops, fertilizers, and water requirements. Do not provide information on other crops, "
            f"pesticides, or unrelated topics."
        )

        try:
            # Make request to Mistral AI
            response = make_request_with_retry(
                client=client,
                model="mistral-large-latest",
                messages=[{"role": "user", "content": prompt}]
            )
            ai_response = response.choices[0].message.content

            # Optional: Validate response to ensure it adheres to restrictions
            restricted_keywords = ["pesticide", "herbicide", "wheat", "corn", "rice"]  # Add more as needed
            if any(keyword in ai_response.lower() for keyword in restricted_keywords):
                return Response(
                    {"error": "AI response contains restricted information"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            return Response(
                {
                    "acres": acres,
                    "disease": disease,
                    "recommendations": ai_response
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

