document.addEventListener('DOMContentLoaded', function() {
    const csrftoken = getCookie('csrftoken'); // Hàm lấy CSRF token

    // --- Like Post ---
    document.querySelectorAll('.like-btn').forEach(button => {
        button.addEventListener('click', function() {
            const postId = this.dataset.postId;
            fetch(`/api/post/${postId}/like/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken,
                    'Content-Type': 'application/json'
                },
            })
            .then(response => response.json())
            .then(data => {
                if (data.liked) {
                    this.classList.add('text-danger'); // Biểu tượng đỏ [cite: 12]
                    this.querySelector('i').classList.remove('far');
                    this.querySelector('i').classList.add('fas');
                } else {
                    this.classList.remove('text-danger');
                    this.querySelector('i').classList.remove('fas');
                    this.querySelector('i').classList.add('far');
                }
                this.querySelector('.like-count').textContent = data.likes_count;
            })
            .catch(error => console.error('Error liking post:', error));
        });
    });

    // --- Bookmark Post ---
    document.querySelectorAll('.bookmark-btn').forEach(button => {
        button.addEventListener('click', function() {
            const postId = this.dataset.postId;
            fetch(`/api/post/${postId}/bookmark/`, { // URL API cho bookmark
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken,
                    'Content-Type': 'application/json'
                },
            })
            .then(response => response.json())
            .then(data => {
                const icon = this.querySelector('i');
                if (data.bookmarked) {
                    this.classList.add('text-primary'); // Hoặc màu đỏ như yêu cầu [cite: 12]
                    icon.classList.remove('far');
                    icon.classList.add('fas');
                } else {
                    this.classList.remove('text-primary');
                    icon.classList.remove('fas');
                    icon.classList.add('far');
                }
                // Có thể hiển thị thông báo data.message
                // alert(data.message); // Hoặc dùng toast bootstrap
            })
            .catch(error => console.error('Error bookmarking post:', error));
        });
    });

    // --- Add Comment (ví dụ cho form comment trong post_detail.html) ---
    const commentForm = document.getElementById('comment-form'); // Cần đặt ID cho form
    if (commentForm) {
        commentForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const postId = this.dataset.postId; // Cần đặt data-post-id cho form
            const formData = new FormData(this);
            const content = formData.get('content');

            fetch(`/api/post/${postId}/comment/add/`, { // URL API cho add comment
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ content: content })
            })
            .then(response => response.json())
            .then(data => {
                if (data.id) { // Thành công
                    // Thêm comment mới vào danh sách comments trên trang mà không cần load lại
                    const commentsContainer = document.getElementById('comments-list'); // Cần ID cho container
                    const newCommentHtml = `
                        <div class="d-flex mb-2">
                            <img src="${data.author.avatar || '/static/core/images/default_avatar.png'}" class="rounded-circle me-2" width="30" height="30">
                            <div>
                                <strong>${data.author.username}</strong>
                                <p class="mb-0">${data.content}</p>
                                <small class="text-muted">${new Date(data.created_at).toLocaleString()}</small>
                            </div>
                        </div>`;
                    commentsContainer.insertAdjacentHTML('beforeend', newCommentHtml);
                    this.reset(); // Xóa nội dung form
                } else {
                    console.error('Error adding comment:', data.errors);
                }
            })
            .catch(error => console.error('Error submitting comment:', error));
        });
    }

     // --- Share Post ---
    document.querySelectorAll('.share-btn').forEach(button => {
        button.addEventListener('click', function() {
            const postId = this.dataset.postId;
            if (confirm("Bạn có muốn chia sẻ bài viết này về trang cá nhân?")) {
                fetch(`/post/${postId}/share/`, { // Đây là viewปกติ, không phải API nếu reload
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrftoken,
                    },
                })
                .then(response => {
                    if (response.ok) {
                        // Nếu không dùng AJAX để cập nhật UI ngay, thì server sẽ redirect
                        // Nếu view trả về JSON:
                        // return response.json();
                        alert("Bài viết đã được chia sẻ!"); // Thông báo đơn giản
                        window.location.reload(); // Hoặc cập nhật UI động
                    } else {
                        alert("Có lỗi xảy ra khi chia sẻ bài viết.");
                    }
                })
                // .then(data => { // Nếu là JSON response
                //     console.log(data.message);
                //     // Cập nhật UI nếu cần
                // })
                .catch(error => console.error('Error sharing post:', error));
            }
        });
    });


});

// Hàm helper để lấy CSRF token
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