from django.contrib.auth.models import AbstractUser, Group, Permission, BaseUserManager
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils import timezone

# Validator cho email trường DUE
def validate_due_email(value):
    if not value.endswith('@due.udn.vn'):
        raise ValidationError(
            _('%(value)s is not a valid DUE email. It must end with @due.udn.vn'),
            params={'value': value},
        )

class CustomUserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('The Email must be set'))
        if not username:
            raise ValueError(_('The Username must be set'))
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'admin') # <<< GÁN ROLE ADMIN CHO SUPERUSER

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(username, email, password, **extra_fields)

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('user', 'User'),
        ('mod', 'Mod'),
        ('admin', 'Admin'),
    )
    email = models.EmailField(
        _('email address'),
        unique=True,
        validators=[validate_due_email] # Yêu cầu email DUE [cite: 2]
    )
    phone_number = models.CharField(max_length=15, blank=True, null=True) # Không bắt buộc [cite: 2]
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, default='avatars/default_avatar.png')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    # username: có sẵn từ AbstractUser, max_length mặc định là 150, có thể tùy chỉnh
    # password: có sẵn từ AbstractUser

    objects = CustomUserManager()
    groups = models.ManyToManyField(
        Group,
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name="customuser_groups",
        related_query_name="customuser",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name="customuser_permissions",
        related_query_name="customuser",
    )

    def __str__(self):
        return self.username

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, default='avatars/default_avatar.png')
    def __str__(self):
        return f"{self.user.username}'s Profile"

class Follow(models.Model):
    follower = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='following_set', on_delete=models.CASCADE)
    following = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='follower_set', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')

    def __str__(self):
        return f"{self.follower} follows {self.following}"


class Post(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=300, blank=True, null=True)  # Có thể để trống title cho bài share sự kiện
    content = models.TextField(blank=True, null=True)  # Có thể để trống content cho bài share sự kiện
    image = models.ImageField(upload_to='post_images/', blank=True, null=True)
    file_attachment = models.FileField(upload_to='post_files/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    shared_from_post = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='posts_sharing_this'
    )
    original_poster_name = models.CharField(max_length=150, blank=True, null=True)

    shared_event = models.ForeignKey(
        'Event',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='posts_sharing_this_event'
    )

    def __str__(self):
        if self.shared_event:
            return f"{self.author.username} shared event: {self.shared_event.title[:30]}..."
        elif self.shared_from_post:
            return f"{self.author.username} shared post: {self.shared_from_post.title[:30]}..."
        return f"{self.title_or_default()} by {self.author.username}"

    def title_or_default(self):
        if self.title:
            return self.title
        if self.shared_event:
            return f"Chia sẻ sự kiện: {self.shared_event.title}"
        return "Bài viết không có tiêu đề"

    @property
    def likes_count(self):
        return self.likes.count()

    def get_absolute_url(self):
        if self.shared_event:
            return reverse('event_detail', kwargs={'event_id': self.shared_event.pk})
        return reverse('post_detail', kwargs={'post_id': self.pk})

    class Meta:
        ordering = ['-created_at']

class Like(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, related_name='likes', on_delete=models.CASCADE, null=True, blank=True)
    event = models.ForeignKey('Event', related_name='likes', on_delete=models.CASCADE, null=True, blank=True) # Like cho Event
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['user', 'post'], ['user', 'event']] # Để 1 user chỉ like 1 post/event 1 lần

class Comment(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey('Post', related_name='comments_on_post', on_delete=models.CASCADE, null=True, blank=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.post:
            return f"Comment by {self.author.username} on Post {self.post.title}"
        elif self.event:
            return f"Comment by {self.author.username} on Event {self.event.title}"
        return f"Comment by {self.author.username}"

    class Meta:
        ordering = ['created_at']

class Bookmark(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, related_name='bookmarked_by', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')

class EventTag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class Event(models.Model):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, limit_choices_to={'role__in': ['mod', 'admin']})
    title = models.CharField(max_length=255)
    content = models.TextField()
    image = models.ImageField(upload_to='event_images/', blank=True, null=True)
    tags = models.ManyToManyField(EventTag, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    shared_from_event = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shared_events'
    )
    original_event_creator_name = models.CharField(max_length=150, blank=True, null=True)


    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('event_detail', kwargs={'event_id': self.pk})

    @property
    def likes_count(self):
        return self.likes.count()

class Report(models.Model):
    REASON_CHOICES = [
        ('spam', 'Spam hoặc quảng cáo không phù hợp'),
        ('offensive', 'Nội dung phản cảm'),
        ('misinformation', 'Thông tin sai lệch'),
        ('other', 'Khác'),
    ]
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

# --- Models cho Nhắn tin ---
class ChatGroup(models.Model):
    name = models.CharField(max_length=100, blank=True)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='chat_groups')
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_groups', limit_choices_to={'role__in': ['mod', 'admin']}) # [cite: 45]
    is_private_chat = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.is_private_chat and self.members.count() == 2:
            return f"Chat between {self.members.first().username} and {self.members.last().username}"
        return self.name or f"Group {self.id}"


class Message(models.Model):
    group = models.ForeignKey(ChatGroup, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='chat_images/', blank=True, null=True)
    file_attachment = models.FileField(upload_to='chat_files/', blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.sender.username} in {self.group.name or 'private chat'}"

class BlockedUser(models.Model):
    blocker = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='blocking_set', on_delete=models.CASCADE)
    blocked = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='blocked_by_set', on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked')

    def __str__(self):
        return f"{self.blocker.username} blocked {self.blocked.username}"

class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ('USER_REGISTERED', 'Người dùng mới đăng ký'),
        ('POST_CREATED', 'Bài viết mới được tạo'),
        ('POST_DELETED', 'Bài viết đã bị xóa'),
        ('USER_ROLE_CHANGED', 'Vai trò người dùng thay đổi'),
        ('EVENT_CREATED', 'Sự kiện mới được tạo'),
        ('REPORT_RESOLVED', 'Báo cáo đã được xử lý'),
    ]

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='performed_actions', verbose_name="Người thực hiện")
    action_type = models.CharField(max_length=50, choices=ACTION_CHOICES, verbose_name="Loại hành động")
    description = models.TextField(verbose_name="Mô tả chi tiết")
    timestamp = models.DateTimeField(default=timezone.now, verbose_name="Thời điểm")

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Nhật ký hoạt động"
        verbose_name_plural = "Nhật ký hoạt động"

    def __str__(self):
        return f"{self.timestamp.strftime('%Y-%m-%d %H:%M')} - {self.actor.username if self.actor else 'Hệ thống'} - {self.get_action_type_display()}"