from customer import views
from django.conf import settings
from .views import CustomerViewSet, YieldCalculationViewSet
from django.urls import path, include
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'customer/create', CustomerViewSet, basename='customer')
router.register(r'customer/yield-calculations', YieldCalculationViewSet)

urlpatterns = [
    path('', include(router.urls)),

    # ------------------------------ Login/Register Endpoints ------------------------------
    path('customer/login/v1/', views.CustomerLoginAPIView.as_view(), name='customer-login'),
    path('customer/register/', views.RegisterCustomerAPIView.as_view(), name='customer-register'),

    # ------------------------------ Forgot Password Endpoints ------------------------------
    path('customer/send-otp/', views.ForgotPasswordAPIView.as_view(), name='send-otp'),
    path('customer/reset-password/', views.ResetPasswordWithOTPAPIView.as_view(), name='reset-password'),

    # ------------------------------ Community-chat Endpoints ------------------------------
    path('customer/chat-ticket/', views.TicketListCreateAPIView.as_view(), name='chat-ticket'),
    path('customer/all-chat-tickets/', views.ListAllChatTickets.as_view(), name='chat-agency-tickets'),
    path('customer/ticket-detail/<int:pk>/', views.TicketDetailAPIView.as_view(), name='ticket-detail'),
    path('customer/get-ticket-reply/<int:ticket_id>/', views.TicketReplyListAPIView.as_view(), name='get-ticket-reply'),
    path('customer/admin-ticket-reply/<int:ticket_id>/', views.TicketReplyCreateAPIView.as_view(), name='admin-ticket-reply'),

    # ------------------------------ Create-bulk-news Endpoints ------------------------------
    path('customer/news/bulk-create/', views.BulkNewsCreateAPIView.as_view(), name='bulk-news-create'),
    path('customer/news/', views.RandomNewsAPIView.as_view(), name='get-random-news'),

    # ------------------------------ GROK API-Key Endpoints ------------------------------
    path('customer/mistral-api/', views.AIChatView.as_view(), name='potato-crop-lifecycle'),

]