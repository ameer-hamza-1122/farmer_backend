from customer import views
from django.conf import settings
from .views import CustomerViewSet
from django.urls import path, include
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'create', CustomerViewSet, basename='customer')

urlpatterns = [
    path('', include(router.urls)),

    # ------------------------------ Login/Register Endpoints ------------------------------
    path('login/v1/', views.CustomerLoginAPIView.as_view(), name='customer-login'),
    path('register/', views.RegisterCustomerAPIView.as_view(), name='customer-register'),

    # ------------------------------ Forgot Password Endpoints ------------------------------
    path('send-otp/', views.ForgotPasswordAPIView.as_view(), name='send-otp'),
    path('reset-password/', views.ResetPasswordWithOTPAPIView.as_view(), name='reset-password'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)