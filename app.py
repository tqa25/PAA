# app.py

import streamlit as st
from rag_engine import PersonalAssistant
import datetime
import subprocess

# --- Hàm để lấy danh sách model từ Ollama ---
@st.cache_data(ttl=600) # Cache kết quả trong 10 phút để không phải gọi lại liên tục
def get_ollama_models():
    """Lấy danh sách các model có sẵn từ Ollama server."""
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')
        if len(lines) <= 1:
            return []
        models = [line.split()[0] for line in lines[1:]]
        return models
    except (subprocess.CalledProcessError, FileNotFoundError):
        st.error("Không thể kết nối đến Ollama. Hãy đảm bảo Ollama server đang chạy.")
        return []

# --- Cấu hình trang ---
st.set_page_config(page_title="Trợ lý AI Cá nhân", layout="wide")
st.title("📝 Trợ lý AI Cá nhân của bạn")
st.write("Ghi lại nhật ký, hỏi đáp và nhận các gợi ý hữu ích.")


# --- Sidebar: Chứa tất cả các tùy chọn ---
with st.sidebar:
    st.header("Cài đặt Model")

    available_models = get_ollama_models()
    
    if available_models:
        # Lấy model đã chọn từ session state hoặc chọn model đầu tiên
        if 'selected_model' not in st.session_state or st.session_state.selected_model not in available_models:
            st.session_state.selected_model = available_models[0]

        selected_model = st.selectbox(
            "Chọn Model LLM:",
            options=available_models,
            index=available_models.index(st.session_state.selected_model)
        )
        
        # Kích hoạt chế độ Thinking Mode
        thinking_mode = st.toggle("Bật Chế độ Suy nghĩ (/think)", value=False, help="Model sẽ hiển thị quá trình suy luận. Chỉ hoạt động với Qwen3.")

        # THÊM NÚT NÀY:
        debug_mode = st.toggle("Bật Chế độ Debug (Logs)", value=False, help="In log chi tiết của LangChain ra terminal.")

        # Thêm các thanh trượt để tinh chỉnh tham số
        st.subheader("Tham số Sampling")
        
        # Đề xuất các giá trị mặc định dựa trên tài liệu Qwen3
        if thinking_mode:
            default_temp, default_topp, default_presence = (0.6, 0.95, 1.5)
        else:
            default_temp, default_topp, default_presence = (0.7, 0.8, 1.5)

        temperature = st.slider("Temperature", min_value=0.0, max_value=2.0, value=default_temp, step=0.1)
        top_p = st.slider("Top-P", min_value=0.0, max_value=1.0, value=default_topp, step=0.05)
        top_k = st.slider("Top-K", min_value=1, max_value=100, value=20, step=1)
        presence_penalty = st.slider("Presence Penalty", min_value=0.0, max_value=2.0, value=default_presence, step=0.1, help="Giảm sự lặp lại của model.")
        
        # Logic để khởi tạo lại assistant chỉ khi có thay đổi
        current_params = (selected_model, temperature, top_p, top_k, presence_penalty)
        if 'last_params' not in st.session_state:
            st.session_state.last_params = ()

        if current_params != st.session_state.last_params:
            st.session_state.selected_model = selected_model
            st.session_state.last_params = current_params
            # Xóa assistant cũ để nó được khởi tạo lại với các tham số mới
            if 'assistant' in st.session_state:
                del st.session_state['assistant']
            st.rerun() # Tải lại trang để áp dụng

    else:
        st.warning("Không tìm thấy model nào. Vui lòng chạy `ollama pull <model_name>`.")
        st.stop() # Dừng chạy app nếu không có model

    st.divider()

    st.header("Thêm nhật ký hôm nay")
    diary_date = st.date_input("Ngày", datetime.date.today())
    diary_content = st.text_area("Hôm nay của bạn thế nào?", height=300)
    
    if st.button("Lưu nhật ký"):
        if diary_content:
            with st.spinner("Đang xử lý và lưu trữ nhật ký..."):
                if 'assistant' not in st.session_state:
                     params = st.session_state.last_params
                     st.session_state.assistant = PersonalAssistant(model_name=params[0], temperature=params[1], top_p=params[2], top_k=params[3], presence_penalty=params[4])
                assistant = st.session_state.assistant
                
                result = assistant.add_diary_entry(diary_content, diary_date.strftime("%Y-%m-%d"))
                st.success(result)
        else:
            st.warning("Vui lòng nhập nội dung nhật ký.")

    st.divider()

    st.header("Thêm Kiến thức mới")
    knowledge_source = st.text_input("Nguồn kiến thức (ví dụ: Wikipedia)", key="kb_source")
    knowledge_content = st.text_area("Nội dung kiến thức", height=200, key="kb_content")

    # Thay thế toàn bộ khối lệnh 'if st.button("Lưu kiến thức")' bằng đoạn này

    if st.button("Lưu kiến thức"):
        if knowledge_content and knowledge_source:
            with st.spinner("Đang xử lý và lưu trữ kiến thức..."):
                # KIỂM TRA VÀ KHỞI TẠO ASSISTANT NẾU CẦN
                # (Logic này được copy từ phần 'Lưu nhật ký')
                if 'assistant' not in st.session_state:
                    # Lấy tham số đã lưu hoặc dùng giá trị mặc định nếu chưa có
                    if 'last_params' in st.session_state and st.session_state.last_params:
                        params = st.session_state.last_params
                    else:
                        # Tạo một bộ tham số mặc định lần đầu tiên
                        params = (st.session_state.selected_model, 0.7, 0.8, 20, 1.5)
                        st.session_state.last_params = params
                    
                    # Khởi tạo assistant
                    st.session_state.assistant = PersonalAssistant(
                        model_name=params[0], temperature=params[1], top_p=params[2], top_k=params[3], presence_penalty=params[4]
                    )
                
                # Bây giờ, assistant chắc chắn đã tồn tại trong session state
                assistant = st.session_state.assistant
                
                # Gọi hàm để thêm kiến thức
                result = assistant.add_knowledge_document(knowledge_content, knowledge_source)
                st.success(result)
        else:
            st.warning("Vui lòng nhập đầy đủ nội dung và nguồn kiến thức.")
          
    if st.button("Tạo báo cáo & Gợi ý cho ngày mai"):
        with st.spinner("Đang phân tích..."):
             if 'assistant' not in st.session_state:
                    params = st.session_state.last_params
                    st.session_state.assistant = PersonalAssistant(model_name=params[0], temperature=params[1], top_p=params[2], top_k=params[3], presence_penalty=params[4])
             assistant = st.session_state.assistant
             
             report = assistant.get_daily_summary_and_plan()
             st.session_state.report = report


# --- Khởi tạo Trợ lý một cách an toàn ---
if 'assistant' not in st.session_state:
    # Lấy tham số đã lưu hoặc dùng giá trị mặc định nếu chưa có
    if 'last_params' in st.session_state and st.session_state.last_params:
        params = st.session_state.last_params
    else:
        # Tạo một bộ tham số mặc định lần đầu tiên
        params = (st.session_state.selected_model, 0.7, 0.8, 20, 1.5)
        st.session_state.last_params = params
    
    st.session_state.assistant = PersonalAssistant(
        model_name=params[0], temperature=params[1], top_p=params[2], top_k=params[3], presence_penalty=params[4]
    )

assistant = st.session_state.assistant


# ----- Khu vực chính: Chat và Hiển thị báo cáo -----
st.header(f"Trò chuyện cùng Trợ lý (Model: `{st.session_state.selected_model}`)")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Bạn muốn hỏi gì về nhật ký của mình?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Đang suy nghĩ..."):
            # Truyền trạng thái của nút toggle vào hàm query
            response = assistant.query(prompt, thinking_mode=thinking_mode, debug_mode=debug_mode)
            st.markdown(response)
    
    st.session_state.messages.append({"role": "assistant", "content": response})

if 'report' in st.session_state and st.session_state.report:
    st.header("Báo cáo và Gợi ý")
    st.info(st.session_state.report)
    del st.session_state.report