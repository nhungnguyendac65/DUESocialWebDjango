document.addEventListener('DOMContentLoaded', function() {
    const csrftoken = getCookie('csrftoken'); // Đảm bảo hàm getCookie đã tồn tại

    const chatMessagesContainer = document.querySelector('[id^="chat-messages-container-"]');
    const currentGroupId = chatMessagesContainer ? chatMessagesContainer.id.split('-').pop() : null;

    // 1. Tự động cuộn xuống tin nhắn mới nhất
    function scrollToBottom(container) {
        if (container) {
            container.scrollTop = container.scrollHeight; // Cuộn xuống dưới cùng
        }
    }

    if (chatMessagesContainer) {
        // Cuộn xuống dưới cùng khi trang được tải lần đầu
        scrollToBottom(chatMessagesContainer);

        // Sử dụng MutationObserver để tự động cuộn khi có tin nhắn mới được thêm vào (cho AJAX)
        const observer = new MutationObserver(mutations => {
            // Có thể thêm logic kiểm tra xem người dùng có đang tự cuộn lên không
            // Hiện tại, nó sẽ luôn cuộn khi có tin nhắn mới
            scrollToBottom(chatMessagesContainer);
        });
        observer.observe(chatMessagesContainer, { childList: true });
    }

    // 2. Gửi tin nhắn bằng AJAX
    if (currentGroupId) {
        const messageForm = document.getElementById(`message-form-${currentGroupId}`);
        const messageTextarea = document.getElementById(`messageTextarea-${currentGroupId}`);
        const attachmentPreviewContainer = document.getElementById(`attachmentPreview-${currentGroupId}`);

        if (messageForm && messageTextarea) {
            messageForm.addEventListener('submit', function(e) {
                e.preventDefault();
                const formData = new FormData(this);
                const content = formData.get('content');

                if (!content.trim() && !formData.get('image') && !formData.get('file_attachment')) {
                    return;
                }

                fetch(this.action, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': csrftoken
                    }
                })
                .then(response => {
                    if (!response.ok) {
                        return response.json().then(err => { throw new Error(JSON.stringify(err.errors || err)); });
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.sender_username) {
                        const messagesContainer = document.getElementById(`chat-messages-container-${currentGroupId}`);
                        const noMessagesYet = document.getElementById(`no-messages-yet-${currentGroupId}`);
                        if(noMessagesYet) noMessagesYet.style.display = 'none';

                        const messageDiv = document.createElement('div');
                        messageDiv.classList.add('d-flex', 'mb-2', 'justify-content-end');
                        messageDiv.id = `message-${data.id || Date.now()}`;

                        let attachmentHTML = '';
                        if (data.image_url) {
                            attachmentHTML += `
                                <a href="${data.image_url}" data-bs-toggle="lightbox" data-gallery="chat-gallery-${currentGroupId}">
                                    <img src="${data.image_url}" class="img-fluid rounded mb-1" style="max-height: 150px; cursor:pointer;" alt="Hình ảnh">
                                </a>`;
                        }
                        if (data.file_url) {
                            attachmentHTML += `
                                <div class="attachment-bubble p-2 rounded bg-primary-subtle text-primary-emphasis mb-1">
                                    <a href="${data.file_url}" target="_blank" class="text-decoration-none text-white">
                                        <i class="fas fa-file-alt me-1"></i> ${data.file_name || 'File đính kèm'}
                                    </a>
                                </div>`;
                        }

                        messageDiv.innerHTML = `
                            <div class="message-bubble p-2 rounded bg-primary text-white" style="max-width: 70%;">
                                ${attachmentHTML}
                                ${data.message_content ? `<p class="mb-0 small">${data.message_content.replace(/\n/g, '<br>')}</p>` : ''}
                                <small class="message-timestamp d-block text-end mt-1 text-white-50">${new Date(data.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</small>
                            </div>
                            <a href="/profile/${data.sender_username}/" class="flex-shrink-0 align-self-end mb-1 ms-2">
                                <img src="${data.sender_avatar_url}" alt="${data.sender_username}" class="rounded-circle" width="30" height="30" style="object-fit: cover;">
                            </a>
                        `;

                        // SỬA Ở ĐÂY: Thay insertBefore bằng appendChild
                        if(messagesContainer) {
                            messagesContainer.appendChild(messageDiv); // Thêm vào cuối danh sách
                            // scrollToBottom(messagesContainer); // MutationObserver sẽ tự động gọi scrollToBottom
                        }

                        this.reset();
                        if (attachmentPreviewContainer) attachmentPreviewContainer.innerHTML = '';
                        if (messageTextarea) messageTextarea.style.height = 'auto';
                        // scrollToBottom đã được gọi bởi MutationObserver, không cần gọi lại ở đây trừ khi có vấn đề
                    } else {
                        console.error('Lỗi khi gửi tin nhắn:', data.errors || data);
                        alert('Lỗi: ' + (data.errors ? JSON.stringify(data.errors) : 'Không thể gửi tin nhắn.'));
                    }
                })
                .catch(error => {
                    console.error('Lỗi kết nối khi gửi tin nhắn:', error);
                    alert('Đã có lỗi kết nối. Vui lòng thử lại.');
                });
            });

            if (messageTextarea) {
                messageTextarea.addEventListener('input', function () {
                    this.style.height = 'auto';
                    this.style.height = (this.scrollHeight) + 'px';
                });
                messageTextarea.addEventListener('keydown', function(event) {
                    if (event.key === 'Enter' && !event.shiftKey) {
                        event.preventDefault();
                        messageForm.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
                    }
                });
            }
        }
    }

    // ... (phần code xử lý đính kèm file và chặn người dùng giữ nguyên) ...
    // 3. Xử lý nút đính kèm file và ảnh + preview (giữ nguyên)
    if (currentGroupId) {
        const attachFileBtn = document.getElementById(`attachFileBtn-${currentGroupId}`);
        const fileAttachmentInput = document.getElementById(`fileAttachmentInput-${currentGroupId}`);
        const attachImageBtn = document.getElementById(`attachImageBtn-${currentGroupId}`);
        const imageAttachmentInput = document.getElementById(`imageAttachmentInput-${currentGroupId}`);
        const attachmentPreviewContainer = document.getElementById(`attachmentPreview-${currentGroupId}`);

        if(attachFileBtn) attachFileBtn.addEventListener('click', () => fileAttachmentInput.click());
        if(attachImageBtn) attachImageBtn.addEventListener('click', () => imageAttachmentInput.click());

        function displayAttachmentPreview(inputElement, previewContainer) {
            if (inputElement.files && inputElement.files[0]) {
                const file = inputElement.files[0];
                const fileName = file.name;
                let iconClass = "fa-file";
                let isImage = file.type.startsWith("image/");

                if (isImage) iconClass = "fa-file-image";

                previewContainer.innerHTML = `
                    <div class="alert alert-secondary alert-dismissible fade show py-1 px-2 d-flex align-items-center" role="alert" style="font-size: 0.8rem;">
                        <i class="fas ${iconClass} me-2"></i>
                        <span class="flex-grow-1 text-truncate" title="${fileName}">${fileName}</span>
                        <button type="button" class="btn-close btn-sm p-1" data-bs-dismiss="alert" aria-label="Close" onclick="clearFileInput('${inputElement.id}', '${previewContainer.id}')"></button>
                    </div>`;
            }
        }

        if(fileAttachmentInput) {
            fileAttachmentInput.addEventListener('change', function() {
                if(imageAttachmentInput) imageAttachmentInput.value = '';
                displayAttachmentPreview(this, attachmentPreviewContainer);
            });
        }
        if(imageAttachmentInput) {
            imageAttachmentInput.addEventListener('change', function() {
                if(fileAttachmentInput) fileAttachmentInput.value = '';
                displayAttachmentPreview(this, attachmentPreviewContainer);
            });
        }
    }

    // 4. Xử lý nút chặn người dùng (giữ nguyên)
    document.body.addEventListener('click', function(event) {
        if (event.target.matches('.block-user-btn') || event.target.closest('.block-user-btn')) {
            const button = event.target.matches('.block-user-btn') ? event.target : event.target.closest('.block-user-btn');
            const userIdToBlock = button.dataset.userId;
            const groupIdForContext = button.dataset.groupId;

            const confirmationMessage = button.textContent.trim().includes('Bỏ chặn') ? "Bạn có chắc muốn bỏ chặn người này?" : "Bạn có chắc muốn chặn người này không? Bạn sẽ không thể gửi hoặc nhận tin nhắn từ họ.";

            if (confirm(confirmationMessage)) {
                fetch(`/messages/block_user/${userIdToBlock}/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrftoken,
                        'Content-Type': 'application/json'
                    },
                })
                .then(response => response.json())
                .then(data => {
                    if (data.message) {
                        alert(data.message);
                        button.innerHTML = data.blocked_status ? '<i class="fas fa-ban fa-fw me-2"></i>Bỏ chặn người này' : '<i class="fas fa-ban fa-fw me-2"></i>Chặn người này';

                        const messageFormForBlock = document.getElementById(`message-form-${groupIdForContext}`);
                        const messageTextareaForBlock = document.getElementById(`messageTextarea-${groupIdForContext}`);
                        const existingBlockedInfo = document.getElementById(`blocked-info-${groupIdForContext}`);
                        if(existingBlockedInfo) existingBlockedInfo.remove();

                        if (messageFormForBlock && messageTextareaForBlock) {
                            const inputsAndButtons = messageFormForBlock.querySelectorAll('input, textarea, button');
                            if (data.blocked_status) {
                                inputsAndButtons.forEach(el => el.disabled = true);
                                const blockedInfoP = document.createElement('p');
                                blockedInfoP.id = `blocked-info-${groupIdForContext}`;
                                blockedInfoP.className = 'text-danger text-center mt-2 small';
                                blockedInfoP.textContent = 'Bạn đã chặn người này. Bỏ chặn để tiếp tục nhắn tin.';
                                messageFormForBlock.insertAdjacentElement('afterend', blockedInfoP);
                            } else {
                                inputsAndButtons.forEach(el => el.disabled = false);
                            }
                        }
                    } else {
                        alert("Có lỗi xảy ra.");
                    }
                })
                .catch(error => {
                    console.error('Error (un)blocking user:', error);
                    alert('Lỗi kết nối khi (bỏ) chặn người dùng.');
                });
            }
        }
    });

}); // Kết thúc DOMContentLoaded


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

function clearFileInput(inputId, previewContainerId) {
    const inputElement = document.getElementById(inputId);
    const previewContainer = document.getElementById(previewContainerId);
    if (inputElement) inputElement.value = '';
    if (previewContainer) {
        const alertElement = previewContainer.querySelector('.alert');
        if(alertElement) alertElement.remove();
    }
}