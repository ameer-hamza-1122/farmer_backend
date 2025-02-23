from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
# from .views import PostListCreateView, LikeCreateView, CommentCreateView
from post import views

urlpatterns = [
    path('post/create/', views.PostListCreateView.as_view(), name='post-list-create'),
    path('post/like/<int:post_id>/', views.LikeCreateView.as_view(), name='post-like'),
    path('post/comment/<int:post_id>/', views.CommentCreateView.as_view(), name='post-comment'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 
