from authentication import CustomJWTAuthentication, IsCustomer
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import Post, Like, Comment
from .serializers import PostSerializer, LikeSerializer, CommentSerializer

class PostListCreateView(generics.ListCreateAPIView):
    authentication_classes = (CustomJWTAuthentication,)
    permission_classes = (IsCustomer,)
    queryset = Post.objects.all().order_by('-created_at')
    serializer_class = PostSerializer

    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)

class LikeCreateView(APIView):
    authentication_classes = (CustomJWTAuthentication,)
    permission_classes = (IsCustomer,)

    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        like, created = Like.objects.get_or_create(customer=request.user, post=post)
        if not created:
            like.delete()
            return Response({'message': 'Like removed'})
        return Response({'message': 'Post liked'})

class CommentCreateView(generics.CreateAPIView):
    authentication_classes = (CustomJWTAuthentication,)
    permission_classes = (IsCustomer,)
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer

    def perform_create(self, serializer):
        post_id = self.kwargs['post_id']
        post = get_object_or_404(Post, id=post_id)
        serializer.save(customer=self.request.user, post=post)
