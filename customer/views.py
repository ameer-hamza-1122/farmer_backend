import os
import re
import json
import time
import numpy as np
from PIL import Image
from io import BytesIO
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
from tensorflow.keras.models import load_model
from rest_framework.permissions import AllowAny
from tensorflow.keras.preprocessing import image
from django.utils.crypto import get_random_string
from django.utils.decorators import method_decorator
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser
from authentication import CustomJWTAuthentication, IsCustomer
from rest_framework.exceptions import NotFound, PermissionDenied
from tensorflow.keras.applications.densenet import preprocess_input
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from .models import Customer, OneTimePassword, ChatTicket, ChatTicketReply, News, Shop, YieldCalculation, LeafDisease
from rest_framework.generics import CreateAPIView, RetrieveAPIView, ListAPIView
from rest_framework.decorators import action, permission_classes, authentication_classes
from .serializers import CustomerLoginSerializer, CustomerSerializer, RegisterCustomerSerializer,ForgotPasswordSerializer, ResetPasswordWithOTPSerializer, NewsSerializer, ShopSerializer, YieldCalculationSerializer, LeafDiseaseDetectionSerializer


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
        try:
            # Initialize pagination
            paginator = PageNumberPagination()
            paginator.page_size = 20
            
            # Get query parameter for filtering
            subject_filter = request.query_params.get('subject', None)
            
            # Start with all chat tickets
            chat_tickets = ChatTicket.objects.all()
            
            # Apply filter if provided
            if subject_filter:
                chat_tickets = chat_tickets.filter(subject__icontains=subject_filter)
            
            # Apply ordering
            chat_tickets = chat_tickets.order_by('-created_on')
            
            # Apply pagination
            paginated_items = paginator.paginate_queryset(chat_tickets, request)
            
            # Serialize the paginated data
            serializer = serializers.ChatTicketSerializer(paginated_items, many=True)
            
            # Return paginated response
            return paginator.get_paginated_response({
                "message": "Successfully retrieved chat tickets data.",
                "count": len(serializer.data),
                "data": serializer.data
            })
            
        except Exception as e:
            return Response({
                "error": f"Error retrieving chat tickets data: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
            # Initialize pagination
            paginator = PageNumberPagination()
            paginator.page_size = 20
            
            # Get query parameters for filtering
            author_name_filter = request.query_params.get('author_name', None)
            title_filter = request.query_params.get('title', None)
            
            # Start with all news items
            news_items = News.objects.all()
            
            # Apply filters if provided
            if author_name_filter:
                news_items = news_items.filter(author_name__icontains=author_name_filter)
            if title_filter:
                news_items = news_items.filter(title__icontains=title_filter)
            
            # Apply random ordering
            news_items = news_items.order_by(Func(function='RANDOM'))
            
            # Apply pagination
            paginated_items = paginator.paginate_queryset(news_items, request)
            
            # Serialize the paginated data
            serializer = NewsSerializer(paginated_items, many=True)
            
            # Return paginated response
            return paginator.get_paginated_response({
                "message": "Successfully retrieved random news data.",
                "count": len(serializer.data),
                "data": serializer.data
            })
            
        except Exception as e:
            return Response({
                "error": f"Error retrieving news data: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NewsDetailView(APIView):
    authentication_classes = (CustomJWTAuthentication,)
    permission_classes = (IsCustomer,)

    def get(self, request, news_id):
        try:
            news = News.objects.get(id=news_id)
            serializer = NewsSerializer(news)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except News.DoesNotExist:
            return Response({"error": "News not found"}, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({"error": "Invalid News ID"}, status=status.HTTP_400_BAD_REQUEST)


# --------------------- Shop APIView ---------------------

class BulkShopCreateAPIView(APIView):
    authentication_classes = (CustomJWTAuthentication,)
    permission_classes = (IsCustomer,)

    def post(self, request):
        json_file_path = os.path.join(settings.BASE_DIR, 'shop_data.json')
        
        try:
            with open(json_file_path, 'r') as file:
                shop_data = json.load(file)
                # Map JSON field names to model field names
                mapped_data = []
                for item in shop_data:
                    # Sanitize image field
                    image_url = item.get('Image')
                    
                    if image_url is None or image_url == '' or not isinstance(image_url, str) or not re.match(r'^https?://', image_url):
                        image_url = None
                        
                    mapped_item = {
                        'url': item.get('Url', '')[:1000],
                        'name': item.get('Name', '')[:1000],
                        'image': image_url[:1000] if image_url else None,
                        'rating': item.get('Rating', '')[:100],
                        'location': item.get('Location', '')[:1000],
                        'phone_number': item.get('Phone number', '')[:100],
                        'latitude': item.get('Latitude', '')[:100]
                    }
                    mapped_data.append(mapped_item)

                serializer = ShopSerializer(data=mapped_data, many=True)
                if serializer.is_valid():
                    shop_instances = [
                        Shop(**item) for item in serializer.validated_data
                    ]
                    
                    Shop.objects.bulk_create(shop_instances)
                    
                    return Response({
                        "message": f"Successfully created {len(shop_instances)} shop items",
                        "count": len(shop_instances)
                    }, status=status.HTTP_201_CREATED)
                else:
                    print("Serializer errors:", serializer.errors)
                    return Response({
                        "error": "Invalid data",
                        "details": serializer.errors
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
        except FileNotFoundError:
            return Response({"error": "JSON file not found in project directory"}, status=status.HTTP_404_NOT_FOUND)
        except json.JSONDecodeError:
            return Response({"error": "Invalid JSON format in file"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Error processing shop items: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RandomShopsAPIView(APIView):
    authentication_classes = (CustomJWTAuthentication,)
    permission_classes = (IsCustomer,)
    
    def get(self, request):
        try:
            # Initialize pagination
            paginator = PageNumberPagination()
            paginator.page_size = 20
            
            # Get query parameters for filtering
            name_filter = request.query_params.get('name', None)
            location_filter = request.query_params.get('location', None)
            
            # Start with all shops
            shop_items = Shop.objects.all()
            
            # Apply filters if provided
            if name_filter:
                shop_items = shop_items.filter(name__icontains=name_filter)
            if location_filter:
                shop_items = shop_items.filter(location__icontains=location_filter)
            
            # Apply random ordering
            shop_items = shop_items.order_by(Func(function='RANDOM'))
            
            # Apply pagination
            paginated_items = paginator.paginate_queryset(shop_items, request)
            
            # Serialize the paginated data
            serializer = ShopSerializer(paginated_items, many=True)
            
            # Return paginated response
            return paginator.get_paginated_response({
                "message": "Successfully retrieved random shops data.",
                "count": len(serializer.data),
                "data": serializer.data
            })
            
        except Exception as e:
            return Response({
                "error": f"Error retrieving shop data: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ShopDetailView(APIView):
    authentication_classes = (CustomJWTAuthentication,)
    permission_classes = (IsCustomer,)

    def get(self, request, shop_id):
        try:
            shop = Shop.objects.get(id=shop_id)
            serializer = ShopSerializer(shop)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Shop.DoesNotExist:
            return Response({"error": "Shop not found"}, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({"error": "Invalid Shop ID"}, status=status.HTTP_400_BAD_REQUEST)


# --------------------- Mistral API-Key APIView ---------------------

class AIChatView(APIView):
    authentication_classes = (CustomJWTAuthentication,)
    permission_classes = (IsCustomer,)
    
    def post(self, request):
        # Extract disease and phase from request body
        disease = request.data.get('disease')
        phase = request.data.get('phase')

        # Validate disease input (optional)
        if disease and not isinstance(disease, str):
            return Response(
                {"error": "Invalid input: Disease must be a string"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate phase input
        valid_phases = ["Dormancy", "Sprouting", "Vegetative Growth", "Tubering", "Maturation"]
        if not phase:
            return Response(
                {"error": "Crop phase is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        if phase not in valid_phases:
            return Response(
                {"error": f"Invalid phase: Must be one of {', '.join(valid_phases)}"},
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

        # Craft prompt based on phase and disease
        phase_guidelines = {
            "Dormancy": (
                "The potato is in the dormancy phase, a state of rest following the previous harvest. "
                "The tuber preserves energy reserves, with temperature and moisture being critical. "
                "Provide recommendations for maintaining optimal storage conditions (e.g., temperature, humidity) "
                "and preparing tubers for planting. Include any specific actions to prevent disease if present."
            ),
            "Sprouting": (
                "The potato is in the sprouting phase, where eyes develop into tender stems. "
                "Uniform and robust sprouting is essential. Provide recommendations for soil preparation, "
                "planting techniques, water requirements (in liters per hectare), and initial fertilizer needs "
                "(nitrogen, phosphorus, potassium in kg per hectare). Include disease management if applicable."
            ),
            "Vegetative Growth": (
                "The potato is in the vegetative growth phase, with a green canopy expanding rapidly. "
                "Optimal soil moisture, nutrient balance, and disease resistance are key. Provide recommendations "
                "for water requirements (in liters per hectare), fertilizer application (nitrogen, phosphorus, potassium "
                "in kg per hectare), and application schedules. Include disease management strategies if applicable."
            ),
            "Tubering": (
                "The potato is in the tubering phase, where stolons form tubers underground. "
                "Sufficient spacing and controlled environments are critical. Provide recommendations for water "
                "requirements (in liters per hectare), fertilizer application (nitrogen, phosphorus, potassium in kg per hectare), "
                "and soil management. Include disease management strategies if applicable."
            ),
            "Maturation": (
                "The potato is in the maturation phase, preparing for harvest. Timing and crop health are critical. "
                "Provide recommendations for water requirements (in liters per hectare), reducing fertilizer use, "
                "and identifying harvest readiness. Include disease management strategies if applicable."
            )
        }

        prompt = (
            f"The potato crop is in the {phase} phase. "
            f"{f'It is affected by {disease}. ' if disease else ''}"
            f"{phase_guidelines[phase]} "
            f"Focus only on potato crops, water requirements, macro-fertilizer (nitrogen, phosphorus, potassium), "
            f"and disease management (if specified). Provide specific quantities (e.g., kg per hectare or liters per hectare) "
            f"and application schedules where applicable. Do not provide information on other crops, pesticides, or unrelated topics."
        )

        try:
            # Make request to Mistral AI
            response = make_request_with_retry(
                client=client,
                model="mistral-large-latest",
                messages=[{"role": "user", "content": prompt}]
            )
            ai_response = response.choices[0].message.content

            # Validate response to ensure it adheres to restrictions
            restricted_keywords = ["pesticide", "herbicide", "wheat", "corn", "rice"]
            if any(keyword in ai_response.lower() for keyword in restricted_keywords):
                return Response(
                    {"error": "AI response contains restricted information"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            return Response(
                {
                    "phase": phase,
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


# --------------------- Crop-yield-calculator APIView ---------------------

class YieldCalculationViewSet(viewsets.ModelViewSet):
    serializer_class = YieldCalculationSerializer
    authentication_classes = (CustomJWTAuthentication,)
    permission_classes = (IsCustomer,)
    queryset = YieldCalculation.objects.all()
    parser_classes = (MultiPartParser, FormParser)

    def perform_create(self, serializer):
        serializer.save()


# --------------------- Leaf-Disease-Detection APIView ---------------------

# Suppress TensorFlow logs
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

class LeafDiseaseDetectionView(APIView):
    authentication_classes = (CustomJWTAuthentication,)
    permission_classes = (IsCustomer,)

    def post(self, request, *args, **kwargs):
        model = load_model("leaf_disease_model.h5")
        serializer = LeafDiseaseDetectionSerializer(data=request.data)

        class_label = ['Bacteria', 'Fungi', 'Healthy', 'Nematode', 'Pest', 'Phytopthora', 'Virus']

        if serializer.is_valid():
            uploaded_file = serializer.validated_data['image']
            try:
                # Read the file into a BytesIO object
                img_data = uploaded_file.read()
                img_io = BytesIO(img_data)

                # Open the image with PIL
                img = Image.open(img_io).convert('RGB')  # Ensure RGB format
                img = img.resize((256, 256))  # Resize to match model input (256, 256)

                # Convert to array and preprocess
                img_array = image.img_to_array(img)
                img_array = np.expand_dims(img_array, axis=0)  # Add batch dimension
                img_array = preprocess_input(img_array)  # Preprocess for DenseNet

                # Predict
                preds = model.predict(img_array)
                predicted_class = int(preds[0][0] > 0.5) if preds.shape[-1] == 1 else int(np.argmax(preds))

                # Create LeafDisease model instance
                leaf_disease = LeafDisease(
                    image=uploaded_file,
                    Choice=class_label[predicted_class],
                    disease_type=class_label[predicted_class]
                )
                leaf_disease.save()
                
                return Response({'predicted_class': predicted_class, 
                                 "Disease" : class_label[predicted_class]}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

