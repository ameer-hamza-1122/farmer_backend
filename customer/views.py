from django.conf import settings
from customer import serializers
from smtplib import SMTPException
from rest_framework import status
from rest_framework import viewsets
from django.core.mail import send_mail
from rest_framework.views import APIView
from django.core.mail import BadHeaderError
from rest_framework.response import Response
from .models import Customer, OneTimePassword
from rest_framework.permissions import AllowAny
from django.utils.crypto import get_random_string
from django.utils.decorators import method_decorator
from rest_framework.permissions import IsAuthenticated
from authentication import CustomJWTAuthentication, IsCustomer
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.generics import CreateAPIView, RetrieveAPIView, ListAPIView
from rest_framework.decorators import action, permission_classes, authentication_classes
from .serializers import CustomerLoginSerializer, CustomerSerializer, RegisterCustomerSerializer,ForgotPasswordSerializer, ResetPasswordWithOTPSerializer

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
    
    # # Gives detail of the request user only
    # def get_queryset(self):
    #     return Customer.objects.filter(id=self.request.user.id)

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

