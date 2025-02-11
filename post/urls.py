from django.urls import path
from .views import PostListCreateView, LikeCreateView, CommentCreateView

urlpatterns = [
    path('create/', PostListCreateView.as_view(), name='post-list-create'),
    path('like/<int:post_id>/', LikeCreateView.as_view(), name='post-like'),
    path('comment/<int:post_id>/', CommentCreateView.as_view(), name='post-comment'),
]
