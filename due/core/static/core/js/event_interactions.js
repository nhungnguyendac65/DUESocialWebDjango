document.addEventListener('DOMContentLoaded', function() {
    const csrftoken = getCookie('csrftoken'); // Đảm bảo hàm getCookie đã tồn tại

    // Sử dụng event delegation cho tất cả các nút tương tác trên sự kiện
    document.body.addEventListener('click', function(event) {

        // --- Xử lý Like Event ---
        const likeButton = event.target.closest('.like-event-btn');
        if (likeButton) {
            event.preventDefault();
            const eventId = likeButton.dataset.eventId;
            if (!eventId) {
                console.error("Event ID không được tìm thấy trên nút like.");
                return;
            }

            fetch(`/api/event/${eventId}/like/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken,
                    'Content-Type': 'application/json'
                },
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => {
                        console.error("API Error Data (Like Event):", err);
                        throw new Error(err.message || err.detail || JSON.stringify(err));
                    }).catch(() => {
                        throw new Error(`Lỗi HTTP khi like event: ${response.status} ${response.statusText}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                const icon = likeButton.querySelector('i.fa-heart');
                const countSpan = likeButton.querySelector('.like-count');

                if (data.liked) {
                    likeButton.classList.add('text-danger');
                    if (icon) {
                        icon.classList.remove('far');
                        icon.classList.add('fas', 'text-danger');
                    }
                } else {
                    likeButton.classList.remove('text-danger');
                    if (icon) {
                        icon.classList.remove('fas', 'text-danger');
                        icon.classList.add('far');
                    }
                }
                if (countSpan && data.likes_count !== undefined) {
                    countSpan.textContent = data.likes_count;
                }
                 if (data.message) { // Hiển thị thông báo từ server (ví dụ: "Đã lưu sự kiện...")
                    // Bạn có thể thay alert bằng một thông báo tinh tế hơn (Bootstrap toast)
                    // alert(data.message);
                    console.log(data.message);
                 }
            })
            .catch(error => {
                console.error('Lỗi khi thích sự kiện:', error);
                // alert('Có lỗi xảy ra khi thực hiện hành động này. Vui lòng thử lại.');
            });
            return;
        }

        // --- Xử lý nút "Bình luận" trên Event Card (CHỈ ĐIỀU HƯỚNG) ---
        const commentCardButton = event.target.closest('.comment-event-btn');
        if (commentCardButton) {
            event.preventDefault();
            const eventId = commentCardButton.dataset.eventId;
            if (eventId) {
                window.location.href = `/event/${eventId}/`; // Điều hướng đến trang chi tiết sự kiện
            }
            return;
        }

        // --- Xử lý nút "Bình luận" trên trang Event Detail ---
        // Vì đã bỏ chức năng bình luận, nút này trên event_detail.html nếu còn thì không làm gì nhiều
        const commentDetailButton = event.target.closest('.comment-event-btn-detail');
        if (commentDetailButton) {
            const eventId = commentDetailButton.dataset.eventId;
            // Nếu bạn muốn nút này focus vào một vùng nào đó (ví dụ: nếu sau này thêm lại bình luận)
            // const commentSection = document.getElementById(`comments-section-event-${eventId}`);
            // if(commentSection) commentSection.scrollIntoView({ behavior: 'smooth' });
            console.log("Nút bình luận trên trang chi tiết sự kiện được nhấn (chức năng bình luận đã bị loại bỏ).");
            return;
        }

        // --- Xử lý nút Share Event ---
        const shareButton = event.target.closest('.share-event-btn-detail') || event.target.closest('.share-event-btn');
        if (shareButton) {
            event.preventDefault();
            const eventId = shareButton.dataset.eventId;
            if (eventId && confirm("Bạn có muốn chia sẻ sự kiện này về trang cá nhân?")) {
                fetch(`/event/${eventId}/share/`, { // Gọi đến URL share_event
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrftoken,
                    },
                })
                .then(response => {
                    if (response.ok) {
                        // View share_event_view đang redirect, trình duyệt sẽ tự động theo
                        // Nếu không redirect mà trả về JSON, xử lý ở đây
                        // Ví dụ, nếu server trả về message trong JSON:
                        // return response.json().then(data => {
                        //     alert(data.message || "Sự kiện đã được chia sẻ!");
                        //     window.location.reload(); // Hoặc cập nhật UI động
                        // });
                        // Hiện tại view redirect, nên chỉ cần reload để thấy message từ Django messages framework
                        alert("Sự kiện đã được chia sẻ! Trang sẽ được tải lại."); // Thông báo tạm thời
                        window.location.reload();
                    } else {
                        return response.text().then(text => {
                            console.error("Server error on share event:", text);
                            try {
                                const errData = JSON.parse(text);
                                throw new Error(errData.error || errData.detail || "Không thể chia sẻ sự kiện. Vui lòng thử lại.");
                            } catch (e) {
                                throw new Error(text || "Không thể chia sẻ sự kiện. Vui lòng thử lại.");
                            }
                        });
                    }
                })
                .catch(error => {
                    console.error('Lỗi khi chia sẻ sự kiện:', error);
                    alert('Lỗi: ' + error.message);
                });
            }
            return;
        }

    }); // Kết thúc event listener cho document.body

}); // Kết thúc DOMContentLoaded


// Hàm getCookie (phải được định nghĩa đúng và chỉ một lần)
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