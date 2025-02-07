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

    # ------------------------------ Community-chat Endpoints ------------------------------
    path('chat-ticket/', views.TicketListCreateAPIView.as_view(), name='chat-ticket'),
    path('all-chat-tickets/', views.ChatTicketsByAgencyView.as_view(), name='chat-agency-tickets'),
    path('ticket-detail/<int:pk>/', views.TicketDetailAPIView.as_view(), name='ticket-detail'),
    path('get-ticket-reply/<int:ticket_id>/', views.AdminTicketReplyListCreateAPIView.as_view(), name='get-ticket-reply'),
    path('admin-ticket-reply/<int:ticket_id>/', views.TicketReplyAnonymousCreateAPIView.as_view(), name='admin-ticket-reply'),


] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)