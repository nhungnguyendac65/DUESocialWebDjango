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
    # Khai báo phone_number ở đây để nó là một field của form, không phải của Profile model
    phone_number = forms.CharField(max_length=15, required=False, label="Số điện thoại", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Số điện thoại của bạn'}))
    username = forms.CharField(max_length=150, disabled=True, required=False, label="Tên đăng nhập", widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': True}))
    email = forms.EmailField(disabled=True, required=False, label="Email", widget=forms.EmailInput(attrs={'class': 'form-control', 'readonly': True}))

    class Meta:
        model = Profile
        fields = ['avatar'] # <<< CHỈ CÓ 'avatar' Ở ĐÂY (nếu avatar ở Profile)
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
        profile = super().save(commit=False) # Lưu các thay đổi của Profile (chỉ avatar)
        user = profile.user

        user.first_name = self.cleaned_data.get('first_name', user.first_name)
        user.last_name = self.cleaned_data.get('last_name', user.last_name)
        # Cập nhật phone_number cho User model
        user.phone_number = self.cleaned_data.get('phone_number', user.phone_number)

        if commit:
            user.save()
            profile.save() # Chỉ lưu profile nếu có thay đổi (ví dụ avatar)
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

    # def clean_file_attachment(self):
    #     file = self.cleaned_data.get('file_attachment', False)
    #     if file and file.size > 100 * 1024 * 1024:  # 100MB
    #         raise forms.ValidationError("Kích thước file không được vượt quá 100MB.")
    #     return file

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
    # Trường 'reason' sẽ tự động dùng Select widget nếu không chỉ định widget khác
    reason = forms.ChoiceField(
        choices=Report.REASON_CHOICES,
        label="Chọn lý do báo cáo*",
        widget=forms.Select(attrs={'class': 'form-select'}) # Sử dụng class của Bootstrap
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
        required=False, # Cho phép không chọn tag nào
        label="Chọn các thẻ (tags) phù hợp"
    )
    class Meta:
        model = Event # <<< Dòng này cần 'Event' đã được import
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
    # Django đã có sẵn form này, có thể tùy chỉnh nếu cần
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
        # Lấy 'current_user' ra khỏi kwargs TRƯỚC KHI gọi super().__init__
        self.current_user = kwargs.pop('current_user', None) # Dòng này quan trọng
        super().__init__(*args, **kwargs) # Bây giờ kwargs không còn 'current_user' nữa

        # Bạn có thể sử dụng self.current_user ở đây nếu muốn tùy chỉnh queryset của trường 'members'
        # Ví dụ: loại trừ người dùng hiện tại (creator) khỏi danh sách chọn
        if self.current_user:
            self.fields['members'].queryset = CustomUser.objects.filter(is_active=True).exclude(id=self.current_user.id).order_by('username')
        else:
            # Nếu không có current_user (trường hợp hiếm), giữ nguyên queryset ban đầu
            self.fields['members'].queryset = CustomUser.objects.filter(is_active=True).order_by('username')

class AdminUserCreationForm(UserCreationForm): # Vẫn kế thừa UserCreationForm
    # Định nghĩa lại các trường của CustomUser mà bạn muốn admin nhập
    # UserCreationForm đã có sẵn field 'username' với các validation cơ bản.
    # Chúng ta có thể override nó nếu muốn thay đổi widget hoặc label.
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
    # Các trường password1 và password2 đã được UserCreationForm cung cấp.
    # Bạn không cần định nghĩa lại chúng ở đây trừ khi muốn thay đổi hoàn toàn widget/label.
    # UserCreationForm sẽ tự động tạo label "Mật khẩu" và "Xác nhận mật khẩu".
    # Nếu bạn muốn tùy chỉnh placeholder cho chúng, bạn có thể làm trong __init__ hoặc template.

    role = forms.ChoiceField(
        choices=CustomUser.ROLE_CHOICES,
        required=True,
        label="Vai trò*",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta(UserCreationForm.Meta): # Kế thừa Meta từ UserCreationForm
        model = CustomUser # Model là CustomUser
        # ĐỊNH NGHĨA THỨ TỰ HIỂN THỊ CÁC TRƯỜNG
        # UserCreationForm.Meta.fields mặc định là ('username',).
        # Các trường password1 và password2 được thêm vào bởi UserCreationForm.
        # Chúng ta cần liệt kê tất cả các field theo thứ tự mong muốn.
        fields = ('username', 'email', 'phone_number', 'password1', 'password2', 'role')

    # clean_username và clean_email đã có trong CustomUserCreationForm,
    # AdminUserCreationForm kế thừa nên sẽ tự động có.
    # Nếu bạn muốn validation khác cho admin, bạn có thể override chúng ở đây.
    # Ví dụ, admin có thể không cần email @due.udn.vn ? (Tùy yêu cầu của bạn)
    # def clean_email(self):
    #     email = self.cleaned_data.get('email')
    #     # Bỏ hoặc thay đổi validation email cho admin nếu cần
    #     if CustomUser.objects.filter(email__iexact=email).exists():
    #         raise forms.ValidationError("Email này đã được sử dụng.")
    #     return email.lower()

    def save(self, commit=True):
        user = super().save(commit=False) # Gọi save của UserCreationForm
        user.role = self.cleaned_data["role"] # Gán vai trò
        if commit:
            user.save()
            # Đảm bảo Profile được tạo
            Profile.objects.get_or_create(user=user)
        return user