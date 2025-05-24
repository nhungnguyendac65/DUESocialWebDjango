from django.urls import path, include
from . import views
from .views import LikePostAPIView, AddCommentAPIView, BookmarkPostAPIView, like_event_api_view

# Các URL pattern cho API (thường có prefix /api/)
api_urlpatterns = [
    path('post/<int:post_id>/like/', LikePostAPIView.as_view(), name='api_like_post'),
    path('post/<int:post_id>/comment/add/', AddCommentAPIView.as_view(), name='api_add_comment'),
    path('post/<int:post_id>/bookmark/', BookmarkPostAPIView.as_view(), name='api_bookmark_post'),
    path('event/<int:event_id>/like/', views.like_event_api_view, name='api_like_event'),
    # Thêm các API endpoints khác nếu cần
]

urlpatterns = [
    # Auth
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('password-reset/', views.password_reset_request_view, name='password_reset_request'),
    # ... (các URL khác của password reset Django cung cấp)

    # Core
    path('', views.home_view, name='home'),
    path('profile/<str:username>/', views.profile_view, name='profile'),
    path('profile/<str:username>/followers/', views.user_followers_view, name='user_followers'),
    path('profile/<str:username>/following/', views.user_following_view, name='user_following'),

    path('post/create/', views.create_post_view, name='create_post'),
    path('post/<int:post_id>/', views.post_detail_view, name='post_detail'),
    path('post/<int:post_id>/edit/', views.edit_post_view, name='edit_post'),
    path('post/<int:post_id>/delete/', views.delete_post_view, name='delete_post'),
    path('post/<int:post_id>/report/', views.report_post_view, name='report_post'),
    path('post/<int:post_id>/share/', views.share_post_view, name='share_post'),


    path('saved/', views.saved_posts_view, name='saved_posts'),
    path('search/', views.search_view, name='search'),

    # Settings
    path('settings/', views.settings_view, name='settings'),
    path('settings/profile/', views.user_info_update_view, name='settings_user_info'),
    path('settings/password/', views.password_change_view, name='settings_password_change'),

    # Events
    path('events/', views.event_list_view, name='event_list'),
    path('events/create/', views.create_event_view, name='create_event'),
    path('events/my/', views.my_events_view, name='my_events'),
    path('event/<int:event_id>/', views.event_detail_view, name='event_detail'),
    path('event/<int:event_id>/share/', views.share_event_view, name='share_event'),
    path('event/<int:event_id>/edit/', views.edit_event_view, name='edit_event'),
    path('event/<int:event_id>/delete/', views.delete_event_view, name='delete_event'), # Giả sử đã có
    path('event/<int:event_id>/report/', views.report_event_view, name='report_event'), # Giả sử đã có

    # Messaging
    path('messages/', views.message_center_view, name='message_center'),
    path('messages/chat/<int:group_id>/', views.chat_room_view, name='chat_room'),
    path('messages/chat/<int:group_id>/send/', views.send_message_view, name='send_message'),
    path('messages/start_chat/<int:user_id>/', views.start_or_get_private_chat_view, name='start_private_chat'),
    path('messages/block_user/<int:user_id_to_block>/', views.block_user_view, name='block_user'),
    path('messages/chat/<int:group_id>/members/', views.group_members_view, name='group_members'),
    path('messages/chat/<int:group_id>/leave/', views.leave_group_view, name='leave_group_view'),
    path('messages/chat/<int:group_id>/add_members/', views.add_members_to_group_view, name='add_members_to_group'),
    path('messages/chat/<int:group_id>/remove_member/<int:user_id>/', views.remove_member_from_group_view,
         name='remove_member_from_group'),

    # Mod/Admin
    path('mod/create_group_chat/', views.mod_create_group_chat_view, name='mod_create_group_chat'),
    path('mod/reported_posts/', views.reported_posts_view, name='reported_posts'),
    path('mod/report/<int:report_id>/resolve/', views.resolve_report_view, name='resolve_report'),
    path('admin/add_mod/', views.admin_add_mod_view, name='admin_add_mod'),
    path('admin/dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('admin/users/', views.manage_users_view, name='manage_users'),
    path('admin/users/add/', views.admin_add_user_view, name='admin_add_user'),
    path('admin/users/delete/<str:username>/', views.admin_delete_user_view, name='admin_delete_user'),
    path('admin/add_mod/', views.admin_add_mod_view, name='admin_add_mod'),
    path('admin/reported_posts/', views.reported_posts_view, name='reported_posts'),
    path('admin/report/<int:report_id>/resolve/', views.resolve_report_view, name='resolve_report'),

    # Follow
    path('user/<int:user_id>/toggle_follow/', views.toggle_follow_view, name='toggle_follow'),


    # API URLs
    path('api/', include(api_urlpatterns)),
    path('api/event/<int:event_id>/like/', views.like_event_api_view, name='api_like_event'),
]