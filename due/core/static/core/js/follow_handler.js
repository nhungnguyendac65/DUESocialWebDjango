// File: core/static/core/js/follow_handler.js
document.addEventListener('DOMContentLoaded', function() {
    const csrftoken = getCookie('csrftoken'); // Hàm này phải được định nghĩa và hoạt động

    document.body.addEventListener('click', function(event) {
        let button = event.target.closest('.toggle-follow-btn');

        if (button) {
            event.preventDefault();
            const userIdToFollow = button.dataset.userId; // ID của người dùng được follow/unfollow
            const followTextSpan = button.querySelector('.follow-text');
            const iconElement = button.querySelector('i');

            if (!userIdToFollow) {
                console.error("User ID to follow/unfollow không được tìm thấy trên button.");
                return;
            }

            fetch(`/user/${userIdToFollow}/toggle_follow/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken,
                    'Content-Type': 'application/json'
                },
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => {
                        if (err.error) { console.error("API Error:", err.error); alert("Lỗi: " + err.error); }
                        else { console.error("API Error:", err); alert("Có lỗi xảy ra."); }
                        throw new Error(err.error || 'Lỗi không xác định');
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.is_following !== undefined) {
                    // Cập nhật trạng thái nút
                    if (data.is_following) {
                        button.classList.remove('btn-primary', 'btn-info', 'text-white');
                        button.classList.add('btn-outline-secondary');
                        if (followTextSpan) followTextSpan.textContent = 'Bỏ theo dõi';
                        if (iconElement) {
                            iconElement.classList.remove('fa-user-plus');
                            iconElement.classList.add('fa-user-minus');
                        }
                    } else {
                        button.classList.remove('btn-outline-secondary');
                        button.classList.add('btn-info', 'text-white'); // Hoặc btn-primary
                        if (followTextSpan) followTextSpan.textContent = 'Theo dõi';
                        if (iconElement) {
                            iconElement.classList.remove('fa-user-minus');
                            iconElement.classList.add('fa-user-plus');
                        }
                    }

                    // CẬP NHẬT SỐ LƯỢNG NGƯỜI THEO DÕI
                    // userIdToFollow là ID của profile_user mà trang đang hiển thị
                    const followersCountElement = document.getElementById(`profile-followers-count-${userIdToFollow}`);

                    console.log(`Looking for element with ID: profile-followers-count-${userIdToFollow}`); // DEBUG
                    console.log(`Found element:`, followersCountElement); // DEBUG
                    console.log(`Data from server:`, data); // DEBUG

                    if (followersCountElement && data.followers_count !== undefined) {
                        followersCountElement.textContent = data.followers_count;
                        console.log(`Updated followers count to: ${data.followers_count}`); // DEBUG
                    } else {
                        if (!followersCountElement) {
                            console.error(`Element with ID profile-followers-count-${userIdToFollow} NOT FOUND in DOM.`);
                        }
                        if (data.followers_count === undefined) {
                            console.error("API response does NOT contain 'followers_count'.");
                        }
                    }

                } else if (data.error) {
                    console.error("API returned an error:", data.error);
                    alert("Lỗi từ server: " + data.error);
                }
            })
            .catch(error => {
                console.error('Fetch error in toggle_follow:', error);
                alert('Đã có lỗi xảy ra trong quá trình kết nối. Vui lòng thử lại.');
            });
        }
    });
});

// Hàm getCookie
if (typeof getCookie !== 'function') {
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
}