

📁 Cấu Trúc Thư Mục

project/
├── app.py              # Main Streamlit application
├── backend.py          # Backend logic và API calls
├── chat_history.json   # File lưu lịch sử (tự tạo)
└── README.md          # File này


1. Quản lý Model AI

Mô tả: Tự động phát hiện và liệt kê các model đã cài đặt trong Ollama
Cách hoạt động:

Kết nối với Ollama API để lấy danh sách model
Hiển thị dropdown cho phép chọn model khác nhau trong một phiên chat
Xử lý lỗi khi không kết nối được với Ollama hoặc không có model nào



2. Quản lý phiên Chat (Session Management)

Mô tả: Hệ thống quản lý nhiều cuộc hội thoại độc lập
Cách hoạt động:

Mỗi phiên có ID duy nhất (UUID) và tên riêng
Lưu trữ lịch sử tin nhắn riêng biệt cho từng phiên
Tự động tạo tên phiên theo thời gian (Phiên mới HH:MM:SS)
Theo dõi phiên hiện tại và thời gian cập nhật cuối



3. Lưu trữ lịch sử Chat

Mô tả: Lưu trữ toàn bộ lịch sử chat vào file JSON local
Cách hoạt động:

File chat_history.json chứa tất cả sessions và messages
Tự động lưu sau mỗi tin nhắn
Khôi phục lại lịch sử khi khởi động ứng dụng
Giới hạn tối đa 200 tin nhắn mỗi phiên để tối ưu performance



4. Giao diện Sidebar tương tác

Mô tả: Sidebar chứa các tính năng quản lý và điều hướng
Các thành phần:

Chọn Model: Dropdown để chuyển đổi AI model
Nút tạo phiên mới: Tạo cuộc hội thoại mới với một click
Lịch sử phiên: Expander hiển thị danh sách các phiên chat



5. Menu ngữ cảnh cho từng phiên

Mô tả: Popover menu cho mỗi phiên chat với các tùy chọn
Tính năng:

Đổi tên phiên: Nhập tên mới và lưu
Xóa nội dung: Xóa toàn bộ tin nhắn trong phiên (giữ lại phiên)
Xóa phiên: Xóa hoàn toàn phiên chat



6. Streaming Response

Mô tả: Hiển thị phản hồi AI theo thời gian thực
Cách hoạt động:

Sử dụng Ollama streaming API
Cập nhật từng token một vào placeholder
Xử lý lỗi khi model không phản hồi



7. Dark Theme UI

Mô tả: Giao diện tối hiện đại và thân thiện với mắt
Đặc điểm:

Màu nền tối (#1e1f20)
Button hover effects với màu xanh (#8ab4f8)
Responsive layout cho session rows
Typography tối ưu cho dark mode