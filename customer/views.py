import json
import os
from django.conf import settings
from customer import serializers
from rest_framework import status
from smtplib import SMTPException
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
    def post(self, request):
        # Path to JSON file in the project's base directory
        json_file_path = os.path.join(settings.BASE_DIR, 'article_details.json')
        
        try:
            # Read the JSON file
            with open(json_file_path, 'r') as file:
                news_data = json.load(file)
                print("Raw JSON data:", news_data)  # Debug: Check the loaded data
                
                # Map JSON field names to model field names
                mapped_data = []
                for item in news_data:
                    mapped_item = {
                        'url': item.get('URL', ''),  # Use .get() with default empty string
                        'title': item.get('Title', ''),
                        'image': item.get('Image'),  # Optional field
                        'description': item.get('Description', ''),
                        'author_image': item.get('Author Image'),  # Optional field
                        'author_name': item.get('Author Name', ''),
                        'author_description': item.get('Author Description', '')
                    }
                    mapped_data.append(mapped_item)
                
                print("Mapped data:", mapped_data)  # Debug: Check the mapped data

                # Validate the data
                serializer = NewsSerializer(data=mapped_data, many=True)
                if serializer.is_valid():
                    news_instances = [
                        News(
                            url=item['url'],
                            title=item['title'],
                            image=item.get('image'),
                            description=item['description'],
                            author_image=item.get('author_image'),
                            author_name=item['author_name'],
                            author_description=item['author_description']
                        ) for item in serializer.validated_data
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

