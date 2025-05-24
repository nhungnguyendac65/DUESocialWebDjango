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
                    this.classList.add('text-danger');
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
            fetch(`/api/post/${postId}/bookmark/`, {
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
                    this.classList.add('text-primary');
                    icon.classList.remove('far');
                    icon.classList.add('fas');
                } else {
                    this.classList.remove('text-primary');
                    icon.classList.remove('fas');
                    icon.classList.add('far');
                }
            })
            .catch(error => console.error('Error bookmarking post:', error));
        });
    });

    // --- Add Comment ---
    const commentForm = document.getElementById('comment-form');
    if (commentForm) {
        commentForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const postId = this.dataset.postId;
            const formData = new FormData(this);
            const content = formData.get('content');

            fetch(`/api/post/${postId}/comment/add/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ content: content })
            })
            .then(response => response.json())
            .then(data => {
                if (data.id) {
                    const commentsContainer = document.getElementById('comments-list');
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
                    this.reset();
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
                fetch(`/post/${postId}/share/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrftoken,
                    },
                })
                .then(response => {
                    if (response.ok) {
                        alert("Bài viết đã được chia sẻ!");
                        window.location.reload();
                    } else {
                        alert("Có lỗi xảy ra khi chia sẻ bài viết.");
                    }
                })
                .catch(error => console.error('Error sharing post:', error));
            }
        });
    });


});

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