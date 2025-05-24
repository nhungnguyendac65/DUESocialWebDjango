from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm
from .models import CustomUser, Post, Comment, Report, Event, Message, Profile, ChatGroup, EventTag


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        help_text="Bắt buộc. Phải là email trường Đại học Kinh tế Đà Nẵng (đuôi due.udn.vn)."
    )
    username = forms.CharField(
        required=True,
        max_length=20,
        help_text="Bắt buộc. Dưới 20 ký tự."
    )
    phone_number = forms.CharField(required=False, max_length=15)

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'phone_number')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email.endswith('@due.udn.vn'):
            raise forms.ValidationError("Email phải có đuôi @due.udn.vn.")
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("Email này đã được sử dụng.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if len(username) > 20:
            raise forms.ValidationError("Tên đăng nhập không được vượt quá 20 ký tự.")
        return username


class CustomUserChangeForm(forms.ModelForm):
    first_name = forms.CharField(max_length=100, required=False, label="Tên", widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=100, required=False, label="Họ", widget=forms.TextInput(attrs={'class': 'form-control'}))
    phone_number = forms.CharField(max_length=15, required=False, label="Số điện thoại", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Số điện thoại của bạn'}))
    username = forms.CharField(max_length=150, disabled=True, required=False, label="Tên đăng nhập", widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': True}))
    email = forms.EmailField(disabled=True, required=False, label="Email", widget=forms.EmailInput(attrs={'class': 'form-control', 'readonly': True}))

    class Meta:
        model = Profile
        fields = ['avatar']
        widgets = {
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        profile_instance = kwargs.get('instance') # instance là Profile
        user_instance = None
        if profile_instance and hasattr(profile_instance, 'user'):
            user_instance = profile_instance.user

        super().__init__(*args, **kwargs)

        if user_instance:
            self.fields['first_name'].initial = user_instance.first_name
            self.fields['last_name'].initial = user_instance.last_name
            self.fields['username'].initial = user_instance.username
            self.fields['email'].initial = user_instance.email
            # Lấy initial cho phone_number từ CustomUser
            self.fields['phone_number'].initial = user_instance.phone_number

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user

        user.first_name = self.cleaned_data.get('first_name', user.first_name)
        user.last_name = self.cleaned_data.get('last_name', user.last_name)
        user.phone_number = self.cleaned_data.get('phone_number', user.phone_number)

        if commit:
            user.save()
            profile.save()
        return profile


class PostForm(forms.ModelForm):
    title = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Tiêu đề (dưới 300 từ)'}),
        max_length=300
    )
    content = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5, 'placeholder': 'Nội dung bài viết'})
    )
    image = forms.ImageField(required=False)
    file_attachment = forms.FileField(required=False)
    class Meta:
        model = Post
        fields = ['title', 'content', 'image', 'file_attachment']


class CommentForm(forms.ModelForm):
    content = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Viết bình luận...'})
    )

    class Meta:
        model = Comment
        fields = ['content']


class ReportForm(forms.ModelForm):
    reason = forms.ChoiceField(
        choices=Report.REASON_CHOICES,
        label="Chọn lý do báo cáo*",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Vui lòng mô tả chi tiết lý do của bạn...'}),
        required=False,
        label="Mô tả lý do khác"
    )

    class Meta:
        model = Report
        fields = ['reason', 'description']



class EventForm(forms.ModelForm):
    title = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ví dụ: Workshop Lập trình Web'}))
    content = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Mô tả chi tiết sự kiện...'}))
    image = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class':'form-control'}))
    tags = forms.ModelMultipleChoiceField(
        queryset=EventTag.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Chọn các thẻ (tags) phù hợp"
    )
    class Meta:
        model = Event
        fields = ['title', 'content', 'image', 'tags']


class GroupChatCreationForm(forms.ModelForm):
    name = forms.CharField(label="Tên nhóm chat", required=True)
    members = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label="Thêm thành viên"
    )

    class Meta:
        model = ChatGroup
        fields = ['name', 'members']


class MessageForm(forms.ModelForm):
    content = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Nhập tin nhắn...'}),
        required=False
    )
    image = forms.ImageField(required=False)
    file_attachment = forms.FileField(required=False)

    class Meta:
        model = Message
        fields = ['content', 'image', 'file_attachment']


class CustomPasswordResetForm(PasswordResetForm):
    pass


class GroupChatCreationForm(forms.ModelForm):
    name = forms.CharField(
        label="Tên nhóm chat*",
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nhập tên cho nhóm chat của bạn'})
    )
    members = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.filter(is_active=True).order_by('username'),
        widget=forms.CheckboxSelectMultiple,
        label="Thêm thành viên vào nhóm",
        required=False,
        help_text="Giữ Ctrl (hoặc Command trên Mac) để chọn nhiều người. Người tạo nhóm sẽ tự động được thêm vào."
    )

    class Meta:
        model = ChatGroup
        fields = ['name', 'members']

    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('current_user', None) # Dòng này quan trọng
        super().__init__(*args, **kwargs) # Bây giờ kwargs không còn 'current_user' nữa

        if self.current_user:
            self.fields['members'].queryset = CustomUser.objects.filter(is_active=True).exclude(id=self.current_user.id).order_by('username')
        else:
            self.fields['members'].queryset = CustomUser.objects.filter(is_active=True).order_by('username')

class AddMembersToGroupForm(forms.Form):
    members_to_add = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.none(), # Sẽ được cập nhật trong __init__
        widget=forms.CheckboxSelectMultiple,
        label="Chọn thành viên để thêm vào nhóm",
        required=True # Ít nhất phải chọn một người để thêm
    )

    def __init__(self, *args, **kwargs):
        group_instance = kwargs.pop('group', None)
        super().__init__(*args, **kwargs)

        if group_instance:
            current_member_ids = group_instance.members.values_list('id', flat=True)
            self.fields['members_to_add'].queryset = CustomUser.objects.filter(is_active=True)\
                                                                .exclude(id__in=current_member_ids)\
                                                                .order_by('username')
        else:
            self.fields['members_to_add'].queryset = CustomUser.objects.filter(is_active=True).order_by('username')

class AdminUserCreationForm(UserCreationForm):
    username = forms.CharField(
        label="Tên đăng nhập*",
        max_length=20,
        help_text="Bắt buộc. Dưới 20 ký tự.",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tên đăng nhập (dưới 20 ký tự)'})
    )
    email = forms.EmailField(
        label="Địa chỉ Email*",
        required=True,
        help_text="Bắt buộc. Phải là email trường Đại học Kinh tế Đà Nẵng (đuôi due.udn.vn).",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@due.udn.vn'})
    )
    phone_number = forms.CharField(
        label="Số điện thoại",
        required=False,
        max_length=15,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Số điện thoại (không bắt buộc)'})
    )
    role = forms.ChoiceField(
        choices=CustomUser.ROLE_CHOICES,
        required=True,
        label="Vai trò*",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'phone_number', 'password1', 'password2', 'role')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.cleaned_data["role"]
        if commit:
            user.save()
            Profile.objects.get_or_create(user=user)
        return user

