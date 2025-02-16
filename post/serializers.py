from rest_framework import serializers
from .models import Post, Like, Comment

class CommentSerializer(serializers.ModelSerializer):
    customer_name = serializers.ReadOnlyField(source='customer.username')

    class Meta:
        model = Comment
        fields = ['id', 'customer_name', 'text', 'created_at']

class LikeSerializer(serializers.ModelSerializer):
    customer_name = serializers.ReadOnlyField(source='customer.username')

    class Meta:
        model = Like
        fields = ['id', 'customer_name', 'created_at']

class PostSerializer(serializers.ModelSerializer):
    customer_name = serializers.ReadOnlyField(source='customer.username')
    comments = CommentSerializer(many=True, read_only=True)
    likes_count = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ['id', 'customer_name', 'caption', 'image', 'created_at', 'likes_count', 'comments']

    def get_likes_count(self, obj):
        return obj.likes.count()
