from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.db.models import OuterRef, Subquery, Q, Count
from django.db import models
from .models import (ActivityLog,CustomUser, Post, Comment, Like, Bookmark, Follow,
                     Event, EventTag, Report, ChatGroup, Message, BlockedUser, Profile)
from .forms import (CustomUserCreationForm, CustomUserChangeForm, PostForm,
                    CommentForm, ReportForm, EventForm, GroupChatCreationForm,
                    MessageForm, CustomPasswordResetForm, AdminUserCreationForm)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .serializers import PostSerializer, CommentSerializer, EventCommentSerializer
from django.core.paginator import Paginator


# --- Authentication Views ---
def register_view(request): 
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Tạo Profile tự động khi user đăng ký
            Profile.objects.create(user=user)
            # Gán role 'user' mặc định đã được set trong model
            login(request, user)

            ActivityLog.objects.create(
                actor=user,  # Người dùng vừa đăng ký
                action_type='USER_REGISTERED',
                description=f"Người dùng @{user.username} đã đăng ký tài khoản mới."
            )

            messages.success(request, "Đăng ký thành công!")
            return redirect('home') # Chuyển đến trang chủ
        else:
            # In lỗi form ra console để debug nếu cần
            # print(form.errors.as_json())
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = CustomUserCreationForm()
    return render(request, 'core/auth/register.html', {'form': form})

def login_view(request): # [cite: 3, 4]
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            # Xác thực bằng email hoặc username
            user = authenticate(request, username=username, password=password)
            if user is None: # Thử xác thực bằng email
                 try:
                    user_by_email = CustomUser.objects.get(email=username)
                    user = authenticate(request, username=user_by_email.username, password=password)
                 except CustomUser.DoesNotExist:
                    pass

            if user is not None:
                login(request, user)
                messages.info(request, f"Chào mừng {username} quay trở lại.")
                return redirect('home') # Chuyển đến trang chủ [cite: 5]
            else:
                messages.error(request, "Tên đăng nhập hoặc mật khẩu không đúng.")
        else:
            messages.error(request, "Tên đăng nhập hoặc mật khẩu không đúng.")
    else:
        form = AuthenticationForm()
    return render(request, 'core/auth/login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "Bạn đã đăng xuất.")
    return redirect('login')

# Placeholder cho Quên mật khẩu [cite: 3]
def password_reset_request_view(request):
    if request.method == "POST":
        form = CustomPasswordResetForm(request.POST)
        if form.is_valid():
            # Logic gửi email reset (Django có sẵn)
            # form.save(...)
            messages.success(request, "Hướng dẫn đặt lại mật khẩu đã được gửi đến email của bạn (nếu tồn tại).")
            return redirect('login')
    else:
        form = CustomPasswordResetForm()
    return render(request, "core/auth/password_reset_form.html", {"form": form})
# Bạn cần cấu hình thêm các view cho password_reset_done, password_reset_confirm, password_reset_complete


# --- Core Views ---
@login_required
def home_view(request):
    # Sửa 'comments' thành 'comments_on_post' trong prefetch_related
    posts_query = Post.objects.select_related('author__profile').prefetch_related(
        'likes',
        'comments_on_post',  # <<< THAY ĐỔI Ở ĐÂY
        'bookmarked_by'  # Nếu bạn muốn prefetch cả bookmark
    ).order_by('-created_at')

    # Gán thêm is_liked_by_user và is_bookmarked_by_user cho mỗi post
    user_liked_post_ids = set()
    user_bookmarked_post_ids = set()
    if request.user.is_authenticated:
        user_liked_post_ids = set(
            Like.objects.filter(user=request.user, post__isnull=False).values_list('post_id', flat=True))
        user_bookmarked_post_ids = set(Bookmark.objects.filter(user=request.user).values_list('post_id', flat=True))

    posts_list = []
    for post_item in posts_query:
        # Xác định bài viết thực sự để kiểm tra like/bookmark
        post_to_display_interaction = post_item.shared_from if post_item.shared_from else post_item

        if post_to_display_interaction:
            post_to_display_interaction.is_liked_by_user = post_to_display_interaction.id in user_liked_post_ids
            post_to_display_interaction.is_bookmarked_by_user = post_to_display_interaction.id in user_bookmarked_post_ids

        if post_item.shared_from:
            post_item.shared_from = post_to_display_interaction
        else:  # Nếu là bài gốc, gán trực tiếp cho post_item
            post_item.is_liked_by_user = post_item.id in user_liked_post_ids
            post_item.is_bookmarked_by_user = post_item.id in user_bookmarked_post_ids

        posts_list.append(post_item)

    post_form = PostForm()
    context = {
        'posts': posts_list,
        'post_form': post_form,
        'sub_page_title': 'Trang chủ'  # Tùy chọn
    }
    return render(request, 'core/home.html', context)

@login_required
def profile_view(request, username): # [cite: 5]
    profile_user = get_object_or_404(CustomUser, username=username)
    posts = Post.objects.filter(author=profile_user).order_by('-created_at') # [cite: 14]
    is_own_profile = (request.user == profile_user)
    is_following = Follow.objects.filter(follower=request.user, following=profile_user).exists() if request.user.is_authenticated else False
    followers_count = profile_user.follower_set.count() # [cite: 15]
    following_count = profile_user.following_set.count()

    context = {
        'profile_user': profile_user,
        'posts': posts,
        'is_own_profile': is_own_profile,
        'is_following': is_following,
        'followers_count': followers_count,
        'following_count': following_count,
        'post_form': PostForm() if is_own_profile else None # Nút đăng bài trên trang cá nhân [cite: 17]
    }
    return render(request, 'core/profile.html', context)

@login_required
def user_followers_view(request, username):
    profile_user_obj = get_object_or_404(CustomUser.objects.select_related('profile'), username=username)

    # Lấy danh sách User objects là follower
    follower_users_qs = CustomUser.objects.filter(following_set__following=profile_user_obj).order_by('username').distinct()

    # Xử lý is_followed_by_request_user cho mỗi user trong danh sách
    followers_list_processed = []
    if request.user.is_authenticated:
        following_by_request_user_ids = set(Follow.objects.filter(follower=request.user).values_list('following_id', flat=True))
        for user_item in follower_users_qs:
            user_item.is_followed_by_request_user = user_item.id in following_by_request_user_ids
            followers_list_processed.append(user_item)
    else:
        followers_list_processed = list(follower_users_qs)


    paginator = Paginator(followers_list_processed, 15) # Hiển thị 15 người mỗi trang
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'profile_user_page': profile_user_obj, # Đổi tên biến để khớp template
        'relationship_list_page': page_obj,   # Đổi tên biến để khớp template
        'type': 'followers'
    }
    return render(request, 'core/followers_list.html', context)

@login_required
def user_following_view(request, username):
    profile_user_obj = get_object_or_404(CustomUser.objects.select_related('profile'), username=username)

    # Lấy danh sách User objects mà profile_user_obj đang following
    following_users_qs = CustomUser.objects.filter(follower_set__follower=profile_user_obj).order_by('username').distinct()

    following_list_processed = []
    if request.user.is_authenticated:
        following_by_request_user_ids = set(Follow.objects.filter(follower=request.user).values_list('following_id', flat=True))
        for user_item in following_users_qs:
            user_item.is_followed_by_request_user = user_item.id in following_by_request_user_ids
            following_list_processed.append(user_item)
    else:
        following_list_processed = list(following_users_qs)


    paginator = Paginator(following_list_processed, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'profile_user_page': profile_user_obj, # Đổi tên biến
        'relationship_list_page': page_obj,   # Đổi tên biến
        'type': 'following'
    }
    # Có thể dùng chung template followers_list.html hoặc tạo following_list.html riêng
    return render(request, 'core/followers_list.html', context)

@login_required
@require_POST # Chỉ chấp nhận POST request
def create_post_view(request): # [cite: 9, 24]
    form = PostForm(request.POST, request.FILES)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        messages.success(request, "Đăng bài thành công!")
        # Nếu dùng AJAX, trả về JsonResponse
        # For AJAX:
        # serializer = PostSerializer(post, context={'request': request})
        # return JsonResponse({'post': serializer.data}, status=201)
        return redirect(request.META.get('HTTP_REFERER', 'home')) # Quay lại trang trước đó
    else:
        # Xử lý lỗi form, có thể trả về JsonResponse với lỗi nếu dùng AJAX
        # For AJAX:
        # return JsonResponse({'errors': form.errors}, status=400)
        messages.error(request, "Đăng bài thất bại. Vui lòng kiểm tra lại thông tin.")
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")
        return redirect(request.META.get('HTTP_REFERER', 'home'))


@login_required
def post_detail_view(request, post_id):
    # Sửa 'comments__author' thành 'comments_on_post__author' trong prefetch_related
    post = get_object_or_404(
        Post.objects.select_related('author__profile').prefetch_related(
            'likes',
            'comments_on_post__author__profile',
            # <<< THAY ĐỔI Ở ĐÂY: prefetch author của comment và profile của author đó
            'bookmarked_by'
        ),
        id=post_id
    )

    # Lấy danh sách bình luận sử dụng related_name mới
    comments = post.comments_on_post.order_by('created_at')  # <<< THAY ĐỔI Ở ĐÂY

    comment_form = CommentForm()  # Form để người dùng thêm bình luận mới

    edit_post_form = None
    if request.user == post.author:
        edit_post_form = PostForm(instance=post)

    if request.user.is_authenticated:
        post.is_liked_by_user = post.likes.filter(user=request.user).exists()
        post.is_bookmarked_by_user = post.bookmarked_by.filter(user=request.user).exists()
    else:
        post.is_liked_by_user = False
        post.is_bookmarked_by_user = False

    context = {
        'post': post,
        'comments': comments,  # comments này đã được lấy bằng related_name đúng
        'comment_form': comment_form,
        'edit_post_form': edit_post_form,
        'sub_page_title': post.title
    }
    return render(request, 'core/post_detail.html', context)


@login_required
@require_POST
def edit_post_view(request, post_id): # [cite: 18]
    post = get_object_or_404(Post, id=post_id, author=request.user)
    form = PostForm(request.POST, request.FILES, instance=post)
    if form.is_valid():
        form.save()
        messages.success(request, "Bài viết đã được cập nhật.")
        return redirect('post_detail', post_id=post.id)
    else:
        # Xử lý lỗi
        messages.error(request, "Cập nhật thất bại.")
        return render(request, 'core/edit_post_form.html', {'form': form, 'post': post}) # Cần template cho form sửa

@login_required
@require_POST
def delete_post_view(request, post_id): # [cite: 18]
    post = get_object_or_404(Post, id=post_id)
    # Kiểm tra quyền xóa: hoặc là tác giả, hoặc là Mod/Admin
    if post.author == request.user or request.user.role in ['mod', 'admin']:
        if post.shared_from and post.author == request.user: # Xóa bài share [cite: 19]
            post.delete()
            messages.success(request, "Đã xóa bài viết chia sẻ khỏi trang cá nhân của bạn.")
        elif post.author == request.user: # Xóa bài gốc của mình
            post.delete()
            messages.success(request, "Bài viết đã được xóa.")
        elif request.user.role in ['mod', 'admin']: # Mod/Admin xóa bài vi phạm
             post.delete()
             messages.success(request, f"Bài viết của {post.author.username} đã được xóa (bởi {request.user.role}).")
        else:
            messages.error(request, "Bạn không có quyền xóa bài viết này.")
            return HttpResponseForbidden()

        # Nếu dùng AJAX
        # return JsonResponse({'message': 'Post deleted successfully'}, status=200)
        return redirect(request.META.get('HTTP_REFERER', 'home'))
    else:
        messages.error(request, "Bạn không có quyền thực hiện hành động này.")
        return HttpResponseForbidden()


@login_required
def report_post_view(request, post_id): # [cite: 20]
    post = get_object_or_404(Post, id=post_id)
    if post.author == request.user:
        messages.error(request, "Bạn không thể báo cáo bài viết của chính mình.")
        return redirect('post_detail', post_id=post.id)

    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.post = post
            report.save()
            messages.success(request, "Báo cáo của bạn đã được gửi. Mod/Admin sẽ xem xét.") # [cite: 23]
            return redirect('post_detail', post_id=post.id)
    else:
        form = ReportForm()
    return render(request, 'core/report_form.html', {'form': form, 'post': post})


# --- API Views cho AJAX (Like, Comment, Bookmark) ---
class LikePostAPIView(APIView): # [cite: 14]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        like, created = Like.objects.get_or_create(user=request.user, post=post)
        if not created: # Nếu đã like -> unlike
            like.delete()
            liked = False
        else: # Nếu chưa like -> like
            liked = True
        return Response({'liked': liked, 'likes_count': post.likes.count()}, status=status.HTTP_200_OK)


class AddCommentAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]  # Chỉ user đã đăng nhập mới được comment

    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)

        # Truyền request vào context của serializer
        serializer = CommentSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            # Gán author và post khi lưu serializer
            comment = serializer.save(author=request.user, post=post)
            # Trả về dữ liệu của comment vừa tạo (đã được serialize đầy đủ)
            # Truyền lại context={'request': request} để đảm bảo avatar_url đúng
            response_data = CommentSerializer(comment, context={'request': request}).data
            return Response(response_data, status=status.HTTP_201_CREATED)

        # Nếu serializer không valid, trả về lỗi
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BookmarkPostAPIView(APIView): # [cite: 5, 12, 26]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        bookmark, created = Bookmark.objects.get_or_create(user=request.user, post=post)
        if not created:
            bookmark.delete()
            bookmarked = False
            message = "Đã bỏ lưu bài viết."
        else:
            bookmarked = True
            message = "Đã lưu bài viết."
        return Response({'bookmarked': bookmarked, 'message': message}, status=status.HTTP_200_OK)

@login_required
def saved_posts_view(request): # [cite: 5, 26]
    bookmarks = Bookmark.objects.filter(user=request.user).select_related('post__author').order_by('-created_at')
    return render(request, 'core/saved_posts.html', {'bookmarks': bookmarks})

# --- Search View ---
@login_required
def search_view(request): # [cite: 7, 25]
    query = request.GET.get('q')
    post_results = []
    user_results = []
    if query:
        post_results = Post.objects.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        ).distinct().order_by('-created_at')
        user_results = CustomUser.objects.filter(
            Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query)
        ).distinct()
    return render(request, 'core/search_results.html', {
        'query': query,
        'post_results': post_results,
        'user_results': user_results
    })


# --- Settings Views ---
@login_required
def settings_view(request): # [cite: 5, 42]
    return render(request, 'core/settings/settings_base.html')

@login_required
def user_info_update_view(request):
    # Nếu avatar nằm trong model Profile liên kết với User
    profile_instance = request.user.profile # Lấy profile của user hiện tại

    if request.method == 'POST':
        # Truyền request.FILES vào form
        form = CustomUserChangeForm(request.POST, request.FILES, instance=profile_instance) # Hoặc instance=request.user nếu avatar ở CustomUser
        if form.is_valid():
            form.save() # Lưu form (và file ảnh nếu có)
            messages.success(request, "Thông tin cá nhân và ảnh đại diện đã được cập nhật.")
            return redirect('settings_user_info') # Redirect lại chính trang đó để thấy thay đổi
        else:
            messages.error(request, "Cập nhật thất bại. Vui lòng kiểm tra lại thông tin.")
    else:
        form = CustomUserChangeForm(instance=profile_instance) # Hoặc instance=request.user
        form.fields['email'].disabled = True
        form.fields['username'].disabled = True


    return render(request, 'core/settings/user_info_form.html', {
        'form': form,
        'sub_page_title': 'Thông tin người dùng'
    })

@login_required
def password_change_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST) # Truyền request.user vào đây
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Rất quan trọng để user không bị logout!
            messages.success(request, 'Mật khẩu của bạn đã được thay đổi thành công!')
            return redirect('settings_password_change') # Hoặc một trang khác báo thành công
        else:
            # Lỗi sẽ được hiển thị bởi template form nếu bạn dùng {{ form.errors }} hoặc crispy
            messages.error(request, 'Vui lòng sửa các lỗi được chỉ ra.')
    else:
        form = PasswordChangeForm(request.user) # Truyền request.user để form có context
        # Bạn có thể tùy chỉnh placeholder cho form ở đây nếu muốn
        form.fields['old_password'].widget.attrs.update({'placeholder': 'Mật khẩu hiện tại của bạn'})
        form.fields['new_password1'].widget.attrs.update({'placeholder': 'Mật khẩu mới (ít nhất 8 ký tự)'})
        form.fields['new_password2'].widget.attrs.update({'placeholder': 'Xác nhận mật khẩu mới'})

    return render(request, 'core/settings/password_change_form.html', {
        'form': form,
        'sub_page_title': 'Đổi mật khẩu'
    })

# --- Events Views ---
def is_mod_or_admin_user(user):
    return user.is_authenticated and (user.role in ['mod', 'admin'] or user.is_superuser)

@user_passes_test(is_mod_or_admin_user) # Chỉ Mod hoặc Admin
@login_required
def create_event_view(request): # <<< ĐẢM BẢO TÊN HÀM ĐÚNG LÀ 'create_event_view'
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.creator = request.user # Gán người tạo là user hiện tại
            event.save()
            form.save_m2m()  # Cần thiết để lưu ManyToManyField (ví dụ: tags)
            messages.success(request, "Sự kiện đã được tạo thành công!")
            return redirect('event_list') # Hoặc đến trang chi tiết sự kiện nếu có
        else:
            messages.error(request, "Tạo sự kiện thất bại. Vui lòng kiểm tra lại thông tin.")
    else:
        form = EventForm()

    context = {
        'form': form,
        'sub_page_title': 'Tạo sự kiện mới'
    }
    return render(request, 'core/events/create_event_form.html', context)


@login_required
def event_list_view(request):
    # Bỏ 'comments_on_event' hoặc 'comments' khỏi prefetch_related
    events_query = Event.objects.select_related('creator__profile').prefetch_related('tags', 'likes').order_by(
        '-created_at')
    all_tags = EventTag.objects.all().order_by('name')

    selected_tag_id = request.GET.get('tag_filter')
    selected_tag_object = None

    if selected_tag_id:
        try:
            selected_tag_id_int = int(selected_tag_id)
            selected_tag_object = get_object_or_404(EventTag, id=selected_tag_id_int)
            events_query = events_query.filter(tags=selected_tag_object)
        except (ValueError, TypeError, EventTag.DoesNotExist):
            messages.error(request, "Tag lọc không hợp lệ.")
            selected_tag_object = None

    liked_event_ids_by_current_user = set()
    if request.user.is_authenticated:
        liked_event_ids_by_current_user = set(
            Like.objects.filter(user=request.user, event__isnull=False).values_list('event_id', flat=True)
        )

    final_events_list = []
    for event_item in events_query:
        event_item.is_liked_by_user = event_item.id in liked_event_ids_by_current_user
        # Không cần gán event_item.comments_count ở đây nữa
        final_events_list.append(event_item)

    context = {
        'events': final_events_list,
        'available_tags': all_tags,
        'selected_tag_object': selected_tag_object,
        'can_create_event': request.user.role in ['mod', 'admin']
    }
    return render(request, 'core/events/event_list.html', context)


@login_required
def my_events_view(request):
    # Lấy các sự kiện mà người dùng hiện tại đã "like"
    liked_event_ids = Like.objects.filter(user=request.user, event__isnull=False).values_list('event_id', flat=True)
    my_liked_events = Event.objects.filter(id__in=liked_event_ids).select_related('creator__profile').prefetch_related('tags', 'likes').order_by('-created_at')

    for event_item in my_liked_events: # Đổi tên biến để tránh xung đột với biến 'event' trong template nếu có
        event_item.is_liked_by_user = True # Vì đây là danh sách event đã like

    context = {
        'my_liked_events': my_liked_events,
        'sub_page_title': 'Sự kiện của tôi'
    }
    return render(request, 'core/events/my_events.html', context)


@login_required
def event_detail_view(request, event_id):
    event = get_object_or_404(Event.objects.select_related('creator__profile').prefetch_related('tags', 'likes'),
                              id=event_id)  # Bỏ prefetch comments

    is_liked_by_current_user = False
    if request.user.is_authenticated:
        is_liked_by_current_user = Like.objects.filter(user=request.user, event=event).exists()
    event.is_liked_by_user = is_liked_by_current_user

    # XÓA HOẶC COMMENT OUT CÁC DÒNG LIÊN QUAN ĐẾN BÌNH LUẬN SỰ KIỆN
    # event_comments = None
    # comment_form = None

    context = {
        'event': event,
        # 'event_comments': event_comments, # Bỏ
        # 'comment_form': comment_form,       # Bỏ
        'sub_page_title': event.title
    }
    return render(request, 'core/events/event_detail.html', context)

@login_required
@require_POST
def like_event_api_view(request, event_id): # [cite: 32]
    event = get_object_or_404(Event, id=event_id)
    like, created = Like.objects.get_or_create(user=request.user, event=event)
    if not created:
        like.delete()
        liked = False
        message = "Đã bỏ lưu sự kiện khỏi 'Sự kiện của tôi'."
    else:
        liked = True
        message = "Sự kiện đã được lưu vào 'Sự kiện của tôi'."
    return JsonResponse({'liked': liked, 'likes_count': event.likes.count(), 'message': message})

@login_required
@require_POST # Đảm bảo chỉ nhận POST request
def share_event_view(request, event_id):
    original_event = get_object_or_404(Event, id=event_id)
    try:
        shared_event_title = f"Đã chia sẻ: {original_event.title}"
        if len(shared_event_title) > 255: # Giới hạn chiều dài tiêu đề
            shared_event_title = shared_event_title[:252] + "..."

        shared_event = Event.objects.create(
            creator=request.user, # Người chia sẻ là người tạo của "bản share" này
            title=shared_event_title,
            content=original_event.content, # Nội dung có thể là của sự kiện gốc
            image=original_event.image,     # Có thể dùng lại ảnh
            shared_from_event=original_event,
            original_event_creator_name=original_event.creator.get_full_name() or original_event.creator.username
            # Tags có thể không cần copy qua, hoặc bạn có thể copy:
            # new_event.tags.set(original_event.tags.all()) sau khi new_event.save()
        )
        # Nếu Event có tags và bạn muốn copy:
        # shared_event.tags.set(original_event.tags.all())

        messages.success(request, "Sự kiện đã được chia sẻ thành công!")
    except Exception as e:
        messages.error(request, f"Không thể chia sẻ sự kiện: {e}")
        # Có thể log lỗi ở đây
        print(f"Error sharing event: {e}")


    return redirect(request.META.get('HTTP_REFERER', 'event_list')) # Quay lại trang trước đó

# --- Messaging Views ---
@login_required
def message_center_view(request):
    current_user = request.user

    # Lấy tin nhắn cuối cùng cho mỗi group để sắp xếp và hiển thị preview
    latest_message_subquery = Message.objects.filter(
        group=OuterRef('pk')
    ).order_by('-timestamp').values('content')[:1]

    latest_message_timestamp_subquery = Message.objects.filter(
        group=OuterRef('pk')
    ).order_by('-timestamp').values('timestamp')[:1]

    user_chat_groups = current_user.chat_groups.prefetch_related(
        'members__profile',  # Lấy profile của các member
    ).annotate(
        last_message_content_sub=Subquery(latest_message_subquery),
        last_message_time_sub=Subquery(latest_message_timestamp_subquery)
    ).order_by(models.F('last_message_time_sub').desc(nulls_last=True), '-created_at')

    private_chats_list = []
    group_chats_list = []

    for group_instance in user_chat_groups:  # Đổi tên biến lặp để rõ ràng hơn
        # Gán thông tin last message
        group_instance.last_message_content = group_instance.last_message_content_sub or "Chưa có tin nhắn"
        group_instance.last_message_time = group_instance.last_message_time_sub or group_instance.created_at

        if group_instance.is_private_chat:
            if group_instance.members.count() == 2:  # Chỉ xử lý private chat có đúng 2 thành viên
                # Tìm người kia trong chat 1-1
                other_user_in_chat = group_instance.members.exclude(id=current_user.id).first()
                if other_user_in_chat:
                    # GÁN THUỘC TÍNH `other_user` CHO ĐỐI TƯỢNG GROUP
                    group_instance.other_user = other_user_in_chat
                    private_chats_list.append(group_instance)
            # else: Bỏ qua các private chat không hợp lệ (ví dụ: chỉ có 1 thành viên)
        else:  # Group chat nhiều người
            group_chats_list.append(group_instance)

    # Lấy danh sách user để bắt đầu chat mới (giữ nguyên logic của bạn)
    blocked_users_by_me_ids = BlockedUser.objects.filter(blocker=current_user).values_list('blocked_id', flat=True)
    users_who_blocked_me_ids = BlockedUser.objects.filter(blocked=current_user).values_list('blocker_id', flat=True)

    all_users_for_new_chat = CustomUser.objects.exclude(id=current_user.id) \
        .exclude(id__in=blocked_users_by_me_ids) \
        .exclude(id__in=users_who_blocked_me_ids) \
        .select_related('profile') \
        .order_by('username')

    create_group_chat_form = None
    if current_user.is_authenticated and current_user.role in ['mod', 'admin']:
        create_group_chat_form = GroupChatCreationForm(current_user=current_user)

    context = {
        'private_chats': private_chats_list,  # Đổi tên biến context cho nhất quán
        'group_chats': group_chats_list,  # Đổi tên biến context cho nhất quán
        'all_users_for_chat': all_users_for_new_chat,
        'create_group_chat_form': create_group_chat_form,
        'sub_page_title': 'Tin nhắn',
    }
    return render(request, 'core/messaging/message_center.html', context)
@login_required
def chat_room_view(request, group_id):
    group = get_object_or_404(ChatGroup.objects.prefetch_related('members', 'messages__sender__profile'), id=group_id)
    if request.user not in group.members.all():
        return HttpResponseForbidden("Bạn không phải là thành viên của nhóm chat này.")

    # Kiểm tra chặn 2 chiều cho chat 1-1
    other_user = None
    if group.is_private_chat:
        other_user = group.members.exclude(id=request.user.id).first()
        if other_user:
            if BlockedUser.objects.filter(blocker=request.user, blocked=other_user).exists() or \
               BlockedUser.objects.filter(blocker=other_user, blocked=request.user).exists():
                messages.error(request, "Bạn không thể nhắn tin với người dùng này do đã chặn hoặc bị chặn.")
                return redirect('message_center')


    messages_list = group.messages.order_by('timestamp')
    message_form = MessageForm()

    context = {
        'group': group,
        'messages_list': messages_list,
        'message_form': message_form,
        'other_user': other_user, # Cho chat 1-1
        'is_creator': group.creator == request.user if group.creator else False, # [cite: 40]
    }
    return render(request, 'core/messaging/chat_room.html', context)

@login_required
@require_POST
def send_message_view(request, group_id): # [cite: 36]
    group = get_object_or_404(ChatGroup, id=group_id)
    if request.user not in group.members.all():
        return JsonResponse({'error': 'Forbidden'}, status=403)

    form = MessageForm(request.POST, request.FILES)
    if form.is_valid():
        message = form.save(commit=False)
        message.sender = request.user
        message.group = group
        message.save()
        # For AJAX response
        return JsonResponse({
            'message_content': message.content,
            'sender_username': message.sender.username,
            'sender_avatar_url': message.sender.profile.avatar.url if hasattr(message.sender, 'profile') and message.sender.profile.avatar else '/static/path/to/default_avatar.png',
            'timestamp': message.timestamp.strftime('%H:%M, %d/%m/%Y'),
            'image_url': message.image.url if message.image else None,
            'file_url': message.file_attachment.url if message.file_attachment else None,
            'file_name': message.file_attachment.name.split('/')[-1] if message.file_attachment else None,
        }, status=201)
    return JsonResponse({'errors': form.errors}, status=400)


@login_required
def start_or_get_private_chat_view(request, user_id):  # Đổi tên tham số để rõ ràng hơn
    other_user = get_object_or_404(CustomUser, id=user_id)

    if request.user == other_user:
        messages.error(request, "Bạn không thể tự chat với chính mình.")
        return redirect('message_center')

    # Kiểm tra chặn
    if BlockedUser.objects.filter(blocker=request.user, blocked=other_user).exists():
        messages.error(request, f"Bạn đã chặn {other_user.username}. Bỏ chặn để nhắn tin.")
        return redirect('message_center')
    if BlockedUser.objects.filter(blocker=other_user, blocked=request.user).exists():
        messages.error(request, f"{other_user.username} đã chặn bạn.")
        return redirect('message_center')

    # Tìm ChatGroup riêng tư đã tồn tại giữa hai người dùng này
    # Một ChatGroup riêng tư giữa 2 người sẽ có is_private_chat=True và có đúng 2 thành viên là request.user và other_user
    chat_group = ChatGroup.objects.annotate(num_members=Count('members')) \
        .filter(is_private_chat=True, num_members=2) \
        .filter(members=request.user) \
        .filter(members=other_user) \
        .first()

    if not chat_group:
        # Nếu chưa có, tạo group mới
        chat_group = ChatGroup.objects.create(is_private_chat=True, creator=request.user)
        chat_group.members.add(request.user, other_user)
        messages.info(request, f"Đã bắt đầu cuộc trò chuyện với {other_user.username}.")

    # Chuyển hướng đến phòng chat với group_id đã tìm thấy hoặc vừa tạo
    return redirect('chat_room', group_id=chat_group.id)

@login_required
@require_POST
def block_user_view(request, user_id_to_block): # [cite: 37, 38]
    user_to_block = get_object_or_404(CustomUser, id=user_id_to_block)
    if user_to_block == request.user:
        return JsonResponse({'error': 'Cannot block yourself'}, status=400)

    block, created = BlockedUser.objects.get_or_create(blocker=request.user, blocked=user_to_block)
    if created:
        message = f"Đã chặn {user_to_block.username}."
        blocked_status = True
        # Xóa Follow nếu có
        Follow.objects.filter(follower=request.user, following=user_to_block).delete()
        Follow.objects.filter(follower=user_to_block, following=request.user).delete()
    else: # Unblock
        block.delete()
        message = f"Đã bỏ chặn {user_to_block.username}."
        blocked_status = False

    return JsonResponse({'message': message, 'blocked_status': blocked_status})


@login_required
def group_members_view(request, group_id): # [cite: 39, 40]
    group = get_object_or_404(ChatGroup.objects.prefetch_related('members__profile'), id=group_id)
    if request.user not in group.members.all():
        return HttpResponseForbidden()
    return render(request, 'core/messaging/group_members.html', {'group': group})


@login_required
@require_POST
def leave_group_view(request, group_id):
    group = get_object_or_404(ChatGroup, id=group_id)

    if request.user in group.members.all():
        # Xác định tên hiển thị của group/chat trước khi thay đổi thành viên
        other_member_username = "người dùng không xác định"
        if group.is_private_chat and group.members.count() > 1:
            other_member = group.members.exclude(id=request.user.id).first()
            if other_member:
                other_member_username = other_member.username

        group_name_display = group.name or f"cuộc trò chuyện với @{other_member_username}"

        group.members.remove(request.user)

        if group.is_private_chat:
            messages.success(request,
                             f"Bạn đã xóa cuộc trò chuyện với @{other_member_username} khỏi danh sách của mình.")
        else:
            messages.success(request, f"Bạn đã rời khỏi nhóm '{group_name_display}'.")

        if group.members.count() == 0:  # Nếu không còn ai trong group (kể cả private)
            group.delete()
            # Không cần message ở đây nữa vì nó có thể gây nhầm lẫn nếu user vừa "xóa" chat riêng của họ
            # messages.info(request, f"Cuộc trò chuyện/Nhóm '{group_name_display}' không còn thành viên nào và đã được xóa hoàn toàn.")

    return redirect('message_center')

# --- Mod/Admin specific views ---
@login_required
def mod_create_group_chat_view(request): # [cite: 45]
    if request.user.role not in ['mod', 'admin']:
        return HttpResponseForbidden("Chỉ Mod hoặc Admin mới được tạo nhóm chat chung.")
    if request.method == 'POST':
        form = GroupChatCreationForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.creator = request.user
            group.is_private_chat = False # Đảm bảo đây là group chat
            group.save()
            # Thêm creator vào members nếu chưa có
            members = list(form.cleaned_data['members'])
            if request.user not in members:
                members.append(request.user)
            group.members.set(members)

            messages.success(request, f"Nhóm chat '{group.name}' đã được tạo.")
            return redirect('chat_room', group_id=group.id)
    else:
        form = GroupChatCreationForm()
    return render(request, 'core/messaging/create_group_chat_form.html', {'form': form})


@login_required
def reported_posts_view(request): # Dành cho Mod/Admin [cite: 46]
    if request.user.role not in ['mod', 'admin']:
        return HttpResponseForbidden()
    reports = Report.objects.filter(is_resolved=False).select_related('post__author', 'reporter').order_by('-created_at')
    return render(request, 'core/admin_mod/reported_posts.html', {'reports': reports})

def is_mod_or_admin_user(user): # <<< ĐỊNH NGHĨA HÀM NÀY Ở ĐÂY
    return user.is_authenticated and (user.role in ['mod', 'admin'] or user.is_superuser)
@user_passes_test(is_mod_or_admin_user)
@login_required
@require_POST
def resolve_report_view(request, report_id):
    report = get_object_or_404(Report, id=report_id)
    action = request.POST.get('action')
    post_to_action = report.post

    if action == 'delete_post':
        if post_to_action:
            post_title = post_to_action.title
            post_author_username = post_to_action.author.username  # Lưu lại để dùng trong message

            # Đánh dấu report là đã giải quyết TRƯỚC KHI xóa post
            # Điều này hữu ích nếu bạn muốn ghi lại hành động trước khi đối tượng Report có thể bị xóa theo Post
            report.is_resolved = True
            report.save()  # Lưu trạng thái của report

            post_to_action.delete()  # Xóa Post. Nếu on_delete=CASCADE trên Report.post, report cũng sẽ bị xóa.
            # Nếu on_delete=SET_NULL, report.post sẽ thành None.
            ActivityLog.objects.create(
                actor=request.user,  # Mod/Admin thực hiện
                action_type='POST_DELETED',  # Hoặc 'REPORT_RESOLVED_POST_DELETED'
                description=f"Bài viết '{post_title}' của @{post_author_username} đã bị xóa bởi @{request.user.username} do báo cáo vi phạm."
            )
            messages.success(request,
                             f"Bài viết '{post_title}' của @{post_author_username} đã bị xóa và báo cáo đã được xử lý.")
        else:
            messages.warning(request, "Bài viết liên quan đến báo cáo này không còn tồn tại.")
            # Nếu post không còn, report này vẫn nên được đánh dấu là đã giải quyết
            if not report.is_resolved:  # Chỉ lưu nếu chưa được đánh dấu
                report.is_resolved = True
                report.save()

        # Vì report có thể đã bị xóa cùng với post (do CASCADE),
        # không nên thực hiện thêm hành động nào trên 'report' ở đây nữa nếu post đã bị xóa.
        # Nếu bạn muốn Report KHÔNG bị xóa khi Post bị xóa, hãy đổi on_delete của Report.post thành models.SET_NULL (và cho phép null=True).
        # Khi đó, sau post_to_action.delete(), bạn cần:
        # report.post = None
        # report.is_resolved = True
        # report.save()

    elif action == 'delete_user':
        if post_to_action:
            user_to_delete = post_to_action.author  # Lấy author từ post_to_action, không phải report.post
            username_deleted = user_to_delete.username
            user_to_delete.is_active = False
            user_to_delete.save()
            ActivityLog.objects.create(
                actor=request.user,
                action_type='USER_ROLE_CHANGED',  # Hoặc 'REPORT_RESOLVED_USER_DEACTIVATED'
                description=f"Người dùng @{username_deleted} đã bị vô hiệu hóa bởi @{request.user.username} do báo cáo vi phạm."
            )
            messages.success(request, f"Người dùng '{username_deleted}' đã bị vô hiệu hóa do vi phạm.")
            report.is_resolved = True
            report.save()
        else:
            messages.warning(request, "Bài viết (và người dùng) liên quan đến báo cáo này không còn tồn tại.")
            if not report.is_resolved:
                report.is_resolved = True
                report.save()

    elif action == 'dismiss_report':
        report.is_resolved = True
        report.save()
        ActivityLog.objects.create(
            actor=request.user,
            action_type='REPORT_RESOLVED',
            description=f"Báo cáo cho bài viết (ID: {report.post.id if report.post else 'N/A'}) đã được @{request.user.username} bỏ qua."
        )
        messages.info(request, "Báo cáo đã được bỏ qua và đánh dấu đã xử lý.")

    else:
        messages.error(request, "Hành động không hợp lệ.")
        return redirect('reported_posts')

    return redirect('reported_posts')

def is_admin_user(user):
    return user.is_authenticated and (user.role == 'admin' or user.is_superuser)
# --- Admin specific views ---
@user_passes_test(is_admin_user)
@login_required
def admin_add_mod_view(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')  # Lấy user_id từ form data
        if not user_id:
            messages.error(request, "Vui lòng chọn một người dùng để cấp quyền.")
            # Lấy lại danh sách user để render lại trang với thông báo lỗi
            users_to_select = CustomUser.objects.filter(role='user', is_active=True).select_related('profile').order_by(
                'username')
            return render(request, 'core/admin_mod/add_mod.html', {
                'users_to_select': users_to_select,
                'sub_page_title': 'Thêm Moderator'
            })

        try:
            user_to_promote = get_object_or_404(CustomUser, id=user_id)

            if user_to_promote.role == 'user':
                user_to_promote.role = 'mod'
                # user_to_promote.is_staff = True # Tùy chọn: cho phép Mod truy cập một số phần của Django Admin
                user_to_promote.save()
                messages.success(request,
                                 f"Đã cấp quyền Moderator cho người dùng {user_to_promote.get_full_name() or user_to_promote.username} (@{user_to_promote.username}).")
            elif user_to_promote.role == 'mod':
                messages.warning(request,
                                 f"Người dùng {user_to_promote.get_full_name() or user_to_promote.username} đã là Moderator.")
            else:  # admin hoặc vai trò khác không phải 'user'
                messages.error(request,
                               f"Không thể thay đổi vai trò của người dùng này thành Mod từ vai trò hiện tại của họ ({user_to_promote.get_role_display()}).")

            return redirect('admin_dashboard')  # Hoặc 'manage_users' nếu bạn muốn quay lại trang quản lý user

        except CustomUser.DoesNotExist:
            messages.error(request, "Người dùng được chọn không tồn tại.")
        except Exception as e:
            messages.error(request, f"Đã có lỗi xảy ra: {e}")
            # Lấy lại danh sách user để render lại trang với thông báo lỗi
            users_to_select = CustomUser.objects.filter(role='user', is_active=True).select_related('profile').order_by(
                'username')
            return render(request, 'core/admin_mod/add_mod.html', {
                'users_to_select': users_to_select,
                'sub_page_title': 'Thêm Moderator'
            })

    # GET request: Lấy danh sách user thường để hiển thị
    users_to_select = CustomUser.objects.filter(role='user', is_active=True).select_related('profile').order_by(
        'username')
    context = {
        'users_to_select': users_to_select,
        'sub_page_title': 'Thêm Moderator'
    }
    return render(request, 'core/admin_mod/add_mod.html', context)
# Trang dashboard đơn giản cho admin (có thể mở rộng)
@login_required
def admin_dashboard_view(request):
    if not request.user.is_superuser and request.user.role != 'admin':
        return HttpResponseForbidden()
    # Thống kê cơ bản...
    user_count = CustomUser.objects.count()
    post_count = Post.objects.count()
    pending_reports_count = Report.objects.filter(is_resolved=False).count()
    context = {
        'user_count': user_count,
        'post_count': post_count,
        'pending_reports_count': pending_reports_count,
    }
    return render(request, 'core/admin_mod/admin_dashboard.html', context)


# Follow/Unfollow
@login_required
@require_POST
def toggle_follow_view(request, user_id):
    user_to_follow = get_object_or_404(CustomUser, id=user_id)
    if user_to_follow == request.user:
        return JsonResponse({'error': 'Cannot follow yourself'}, status=400)

    # Kiểm tra chặn
    if BlockedUser.objects.filter(
            Q(blocker=request.user, blocked=user_to_follow) | Q(blocker=user_to_follow, blocked=request.user)).exists():
        return JsonResponse({'error': 'Cannot follow due to blocking'}, status=403)

    follow, created = Follow.objects.get_or_create(follower=request.user, following=user_to_follow)
    is_following = True
    if not created:  # Nếu đã tồn tại -> bỏ theo dõi
        follow.delete()
        is_following = False

    # Lấy số lượng người theo dõi MỚI của user_to_follow
    current_followers_count = user_to_follow.follower_set.count()

    return JsonResponse({
        'is_following': is_following,
        'followers_count': current_followers_count  # <<< TRẢ VỀ SỐ LƯỢNG FOLLOWER MỚI
    })

# Share post
@login_required
@require_POST
def share_post_view(request, post_id): # [cite: 12]
    original_post = get_object_or_404(Post, id=post_id)

    # Kiểm tra xem đã share bài này chưa (để tránh share nhiều lần cùng 1 bài)
    # Tuy nhiên, người dùng có thể muốn share lại sau khi xóa bài share cũ
    # Nên có thể bỏ qua kiểm tra này hoặc có logic phức tạp hơn

    shared_post = Post.objects.create(
        author=request.user,
        title=f"Shared: {original_post.title}", # Hoặc để người dùng nhập tiêu đề mới
        content=original_post.content, # Hoặc cho phép thêm bình luận riêng
        image=original_post.image,
        file_attachment=original_post.file_attachment,
        shared_from=original_post,
        original_poster_name=original_post.author.get_full_name() or original_post.author.username
    )
    messages.success(request, "Bài viết đã được chia sẻ về trang cá nhân của bạn.")
    # Nếu dùng AJAX:
    # serializer = PostSerializer(shared_post, context={'request': request})
    # return JsonResponse({'post': serializer.data, 'message': 'Post shared successfully'}, status=201)
    return redirect(request.META.get('HTTP_REFERER', 'home'))


# Helper function để kiểm tra admin (bạn có thể đã có)
def is_admin_user(user):
    return user.is_authenticated and (user.role == 'admin' or user.is_superuser)


@user_passes_test(is_admin_user)
@login_required
def manage_users_view(request):
    users = CustomUser.objects.all().order_by('username').select_related('profile')

    # Xử lý xóa người dùng nếu có POST request từ form nhập username
    if request.method == 'POST' and 'delete_user_username' in request.POST:
        username_to_delete = request.POST.get('delete_user_username', '').strip()
        if not username_to_delete:
            messages.error(request, "Vui lòng nhập tên đăng nhập của người dùng cần xóa.")
        else:
            try:
                user_to_delete = CustomUser.objects.get(username=username_to_delete)
                if user_to_delete == request.user:
                    messages.error(request, "Bạn không thể tự xóa chính mình.")
                elif user_to_delete.is_superuser and request.user != user_to_delete:  # Chỉ superuser gốc mới xóa được superuser khác (ví dụ)
                    # Hoặc logic: chỉ superuser gốc mới xóa được superuser khác
                    # Nếu người thực hiện không phải là chính người đó VÀ người bị xóa là superuser
                    # thì cần kiểm tra thêm quyền. Để đơn giản, tạm thời cho phép nếu người thực hiện là superuser.
                    if not request.user.is_superuser:
                        messages.error(request, "Chỉ superuser mới có quyền xóa superuser khác.")
                    else:  # Superuser có thể xóa superuser khác (trừ chính mình)
                        deleted_username = user_to_delete.username
                        user_to_delete.delete()
                        messages.success(request, f"Đã xóa thành công người dùng: {deleted_username}")
                        return redirect('manage_users')  # Redirect để làm mới danh sách
                else:  # Người dùng thường hoặc mod
                    deleted_username = user_to_delete.username
                    user_to_delete.delete()
                    messages.success(request, f"Đã xóa thành công người dùng: {deleted_username}")
                    return redirect('manage_users')  # Redirect để làm mới danh sách

            except CustomUser.DoesNotExist:
                messages.error(request, f"Không tìm thấy người dùng với tên đăng nhập: {username_to_delete}")
            except Exception as e:
                messages.error(request, f"Lỗi khi xóa người dùng: {e}")

    context = {
        'users': users,
        'sub_page_title': 'Quản lý Người dùng'
    }
    return render(request, 'core/admin_mod/manage_users.html', context)


@user_passes_test(is_admin_user) # Hoặc decorator kiểm tra quyền admin của bạn
@login_required
def admin_add_user_view(request):
    if request.method == 'POST':
        form = AdminUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            ActivityLog.objects.create(
                actor=request.user,  # Admin thực hiện
                action_type='USER_REGISTERED',  # Hoặc một type khác như 'ADMIN_CREATED_USER'
                description=f"Admin @{request.user.username} đã tạo người dùng mới @{user.username} với vai trò {user.get_role_display()}."
            )
            messages.success(request, f"Đã thêm thành công người dùng: {user.username} với vai trò {user.get_role_display()}.")
            return redirect('manage_users')
        else:
            # Xử lý lỗi form (ví dụ: hiển thị lại form với lỗi)
            for field, errors_list in form.errors.items():
                for error in errors_list:
                    field_label = form.fields[field].label if field in form.fields and field != '__all__' else "Lỗi chung"
                    messages.error(request, f"Lỗi ở trường '{field_label}': {error}")
    else: # GET request
        form = AdminUserCreationForm() # Tạo instance của form mới

    context = {
        'form': form,
        'sub_page_title': 'Thêm Người dùng mới'
    }
    return render(request, 'core/admin_mod/admin_add_user.html', context)

@user_passes_test(is_admin_user)
@login_required
@require_POST  # Đảm bảo chỉ POST request mới xóa được
def admin_delete_user_view(request, username):  # Xóa theo username từ URL
    try:
        user_to_delete = CustomUser.objects.get(username=username)
        if user_to_delete == request.user:
            messages.error(request, "Bạn không thể tự xóa chính mình.")
        elif user_to_delete.is_superuser and not request.user.is_superuser:
            messages.error(request, "Chỉ superuser mới có quyền xóa superuser khác.")
        else:
            deleted_username = user_to_delete.username
            user_to_delete.delete()
            ActivityLog.objects.create(
                actor=request.user,
                action_type='USER_DELETED',
                description=f"Admin @{request.user.username} đã xóa người dùng @{deleted_username}."
            )
            messages.success(request, f"Đã xóa thành công người dùng: {deleted_username}")
    except CustomUser.DoesNotExist:
        messages.error(request, f"Không tìm thấy người dùng: {username}")
    except Exception as e:
        messages.error(request, f"Lỗi khi xóa người dùng: {e}")
    return redirect('manage_users')

@user_passes_test(is_admin_user)
@login_required
def admin_dashboard_view(request):
    user_count = CustomUser.objects.count()
    post_count = Post.objects.count()
    event_count = Event.objects.count()
    pending_reports_count = Report.objects.filter(is_resolved=False).count()

    # Lấy 5 hoạt động gần nhất
    recent_activities = ActivityLog.objects.select_related('actor').order_by('-timestamp')[:5]

    context = {
        'user_count': user_count,
        'post_count': post_count,
        'event_count': event_count,
        'pending_reports_count': pending_reports_count,
        'recent_activities': recent_activities, # Truyền dữ liệu thật
        'sub_page_title': 'Dashboard'
    }
    return render(request, 'core/admin_mod/admin_dashboard.html', context)