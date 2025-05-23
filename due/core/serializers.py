from rest_framework import serializers
from django.contrib.staticfiles.storage import staticfiles_storage
from .models import CustomUser, Post, Comment, Like, Bookmark

class UserSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'first_name', 'last_name', 'avatar_url']

    def get_avatar_url(self, obj):
        request = self.context.get('request')
        if hasattr(obj, 'profile') and obj.profile and obj.profile.avatar and hasattr(obj.profile.avatar, 'url') and obj.profile.avatar.name:
            avatar_url = obj.profile.avatar.url
            return request.build_absolute_uri(avatar_url) if request else avatar_url
        else:

            try:
                placeholder_url = staticfiles_storage.url('core/images/default_placeholder_avatar.png')
                return request.build_absolute_uri(placeholder_url) if request else placeholder_url
            except Exception:
                return None

class PostSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    likes_count = serializers.IntegerField(source='likes.count', read_only=True)
    comments_count = serializers.IntegerField(source='comments.count', read_only=True)
    is_liked = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'title', 'content', 'image', 'file_attachment', 'created_at',
            'author', 'likes_count', 'is_liked', 'is_bookmarked', 'comments_count',
            'shared_from', 'original_poster_name'
        ]

    def get_is_liked(self, obj):
        user = self.context.get('request').user
        if user and user.is_authenticated:
            return Like.objects.filter(post=obj, user=user).exists()
        return False

    def get_is_bookmarked(self, obj):
        user = self.context.get('request').user
        if user and user.is_authenticated:
            return Bookmark.objects.filter(post=obj, user=user).exists()
        return False

class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    content = serializers.CharField(required=True, allow_blank=False, max_length=1000)

    class Meta:
        model = Comment
        fields = ['id', 'post', 'author', 'content', 'created_at']
        read_only_fields = ['author', 'post', 'created_at', 'id']

class EventCommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    content = serializers.CharField(required=True, allow_blank=False, max_length=1000)

    class Meta:
        model = Comment
        fields = ['id', 'event', 'author', 'content', 'created_at']
        read_only_fields = ['author', 'event', 'created_at', 'id']