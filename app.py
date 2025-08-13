# app_optimized.py

import streamlit as st
from rag_engine import OptimizedPersonalAssistant
import config as config
import datetime
import subprocess
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor

# --- Performance Monitoring ---
def log_performance(func_name: str, start_time: float):
    """Log performance metrics"""
    elapsed = time.time() - start_time
    if elapsed > 1.0:  # Log slow operations
        st.sidebar.caption(f"⚡ {func_name}: {elapsed:.2f}s")

# --- Optimized Model Loading ---
@st.cache_data(ttl=300, show_spinner=False)  # Cache for 5 minutes
def get_ollama_models():
    """Optimized model list fetching with timeout"""
    try:
        result = subprocess.run(
            ['ollama', 'list'], 
            capture_output=True, 
            text=True, 
            check=True,
            timeout=10  # 10 second timeout
        )
        
        lines = result.stdout.strip().split('\n')
        if len(lines) <= 1:
            return []
        
        models = []
        for line in lines[1:]:
            parts = line.split()
            if parts:
                model_name = parts[0]
                size_info = parts[1] if len(parts) > 1 else ""
                models.append(f"{model_name} ({size_info})")
        
        return models
        
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return []

# --- Async Operations ---
@st.cache_data(ttl=60)
def get_system_status():
    """Get system status for monitoring"""
    try:
        # Quick health check
        result = subprocess.run(
            ['ollama', 'ps'], 
            capture_output=True, 
            text=True, 
            timeout=5
        )
        running_models = len(result.stdout.strip().split('\n')) - 1
        return f"🟢 Active models: {max(0, running_models)}"
    except:
        return "🔴 Ollama not responding"

# --- Optimized Assistant Initialization ---
def get_or_create_assistant(model_name: str, **params) -> OptimizedPersonalAssistant:
    """Smart assistant initialization with parameter change detection"""
    
    current_params = (model_name, params.get('temperature', 0.7), 
                     params.get('top_p', 0.8), params.get('top_k', 20), 
                     params.get('presence_penalty', 1.5))
    
    # Check if we need to reinitialize
    if ('assistant' not in st.session_state or 
        'last_params' not in st.session_state or
        st.session_state.last_params != current_params):
        
        print(f"[INIT] Creating new assistant with params: {current_params}")
        
        # Clear old assistant
        if 'assistant' in st.session_state:
            del st.session_state.assistant
        
        # Create new assistant
        st.session_state.assistant = OptimizedPersonalAssistant(
            model_name=model_name,
            temperature=params.get('temperature', 0.7),
            top_p=params.get('top_p', 0.8),
            top_k=params.get('top_k', 20),
            presence_penalty=params.get('presence_penalty', 1.5)
        )
        
        st.session_state.last_params = current_params
    
    return st.session_state.assistant

# --- Page Configuration ---
st.set_page_config(
    page_title=config.STREAMLIT_CONFIG['page_title'],
    layout=config.STREAMLIT_CONFIG['layout'],
    initial_sidebar_state=config.STREAMLIT_CONFIG['initial_sidebar_state']
)

# --- Header with Status ---
col1, col2 = st.columns([3, 1])
with col1:
    st.title("🚀 Trợ lý AI Cá nhân (Optimized)")
    st.caption("Phiên bản tối ưu với caching và lazy loading")

with col2:
    status = get_system_status()
    st.metric("System Status", status)

# --- Sidebar: Enhanced Settings ---
with st.sidebar:
    st.header("⚙️ Cài đặt Model")
    
    # Model selection with loading indicator
    with st.spinner("Đang tải danh sách models..."):
        available_models = get_ollama_models()
    
    if not available_models:
        st.error("❌ Không tìm thấy model. Hãy chạy `ollama pull llama3.2:3b`")
        st.stop()
    
    # Extract model names (remove size info)
    model_names = [model.split(' (')[0] for model in available_models]
    model_display = dict(zip(model_names, available_models))
    
    # Model selection
    if 'selected_model' not in st.session_state:
        # Try to find recommended model
        recommended = ['llama3.2:3b', 'gemma2:2b', 'llama3.2:1b']
        for rec in recommended:
            if rec in model_names:
                st.session_state.selected_model = rec
                break
        else:
            st.session_state.selected_model = model_names[0]
    
    selected_model = st.selectbox(
        "Chọn Model LLM:",
        options=model_names,
        format_func=lambda x: model_display[x],
        index=model_names.index(st.session_state.selected_model) if st.session_state.selected_model in model_names else 0
    )
    
    # Model-specific optimization
    model_config = config.get_model_config(selected_model)
    
    # Enhanced controls
    st.subheader("🎛️ Tham số Model")
    
    col1, col2 = st.columns(2)
    with col1:
        thinking_mode = st.toggle("🧠 Thinking Mode", value=False)
        debug_mode = st.toggle("🔍 Debug Mode", value=False)
    
    with col2:
        smart_params = st.toggle("⚡ Auto Optimize", value=True, 
                                help="Sử dụng tham số tối ưu cho model")
    
    # Parameter controls
    if smart_params:
        temperature = model_config['optimal_temperature']
        top_p = model_config['optimal_top_p']
        top_k = model_config['optimal_top_k']
        presence_penalty = 1.2
        
        st.info(f"🎯 Sử dụng tham số tối ưu cho {selected_model}")
        
    else:
        temperature = st.slider("Temperature", 0.0, 2.0, 0.7, 0.1)
        top_p = st.slider("Top-P", 0.0, 1.0, 0.8, 0.05)
        top_k = st.slider("Top-K", 1, 100, 20, 1)
        presence_penalty = st.slider("Presence Penalty", 0.0, 2.0, 1.5, 0.1)
    
    # Initialize assistant
    assistant = get_or_create_assistant(
        selected_model,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        presence_penalty=presence_penalty
    )
    
    st.divider()
    
    # --- Quick Actions ---
    st.header("⚡ Quick Actions")
    
    # Diary entry with enhanced UX
    st.subheader("📝 Nhật ký hôm nay")
    diary_date = st.date_input("Ngày", datetime.date.today())
    diary_content = st.text_area(
        "Hôm nay của bạn thế nào?", 
        height=200,
        placeholder="Ví dụ: Hôm nay tôi dậy lúc 7h, ăn phở sáng, làm việc 8 tiếng, tập gym 30 phút..."
    )
    
    if st.button("💾 Lưu nhật ký", type="primary"):
        if diary_content.strip():
            start_time = time.time()
            with st.spinner("🔄 Đang phân tích và lưu..."):
                result = assistant.add_diary_entry(diary_content, diary_date.strftime("%Y-%m-%d"))
                st.success(result)
                log_performance("Add Diary", start_time)
        else:
            st.warning("⚠️ Vui lòng nhập nội dung nhật ký")
    
    st.divider()
    
    # Knowledge base
    st.subheader("📚 Thêm Kiến thức")
    knowledge_source = st.text_input("Nguồn", placeholder="Wikipedia, Tài liệu, Web...")
    knowledge_content = st.text_area(
        "Nội dung", 
        height=150,
        placeholder="Nhập kiến thức mới..."
    )
    
    if st.button("📖 Lưu kiến thức"):
        if knowledge_content.strip() and knowledge_source.strip():
            start_time = time.time()
            with st.spinner("🔄 Đang lưu kiến thức..."):
                result = assistant.add_knowledge_document(knowledge_content, knowledge_source)
                st.success(result)
                log_performance("Add Knowledge", start_time)
        else:
            st.warning("⚠️ Vui lòng nhập đầy đủ thông tin")
    
    st.divider()
    
    # Smart actions
    st.subheader("🤖 Smart Actions")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 Báo cáo tuần", use_container_width=True):
            start_time = time.time()
            with st.spinner("📈 Đang phân tích..."):
                report = assistant.get_daily_summary_and_plan()
                st.session_state.report = report
                log_performance("Weekly Report", start_time)
    
    with col2:
        if st.button("💪 Phân tích sức khỏe", use_container_width=True):
            start_time = time.time()
            with st.spinner("🏥 Đang phân tích..."):
                health = assistant.get_health_insights()
                st.session_state.health_report = health
                log_performance("Health Analysis", start_time)

# --- Main Chat Interface ---
st.header(f"💬 Chat với {selected_model}")

# Quick action buttons
col1, col2, col3, col4 = st.columns(4)
quick_questions = [
    "📅 Lịch trình hôm nay thế nào?",
    "🍽️ Gợi ý thực đơn healthy",
    "💪 Lên kế hoạch tập luyện",
    "😊 Tâm trạng tôi ra sao?"
]

for i, (col, question) in enumerate(zip([col1, col2, col3, col4], quick_questions)):
    with col:
        if st.button(question, key=f"quick_{i}", use_container_width=True):
            # Add to chat
            if "messages" not in st.session_state:
                st.session_state.messages = []
            
            st.session_state.messages.append({"role": "user", "content": question})
            
            # Get response
            start_time = time.time()
            with st.spinner("🤔 Đang suy nghĩ..."):
                response = assistant.query(question, thinking_mode=thinking_mode, debug_mode=debug_mode)
                st.session_state.messages.append({"role": "assistant", "content": response})
                log_performance("Quick Query", start_time)
            
            st.rerun()

# Chat messages
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Bạn muốn hỏi gì về nhật ký?"):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate response
    with st.chat_message("assistant"):
        start_time = time.time()
        with st.spinner("🤔 Đang suy nghĩ..."):
            response = assistant.query(prompt, thinking_mode=thinking_mode, debug_mode=debug_mode)
            st.markdown(response)
            log_performance("Chat Query", start_time)
    
    st.session_state.messages.append({"role": "assistant", "content": response})

# --- Reports Display ---
if 'report' in st.session_state and st.session_state.report:
    st.header("📊 Báo cáo tuần")
    st.info(st.session_state.report)
    if st.button("🗑️ Xóa báo cáo"):
        del st.session_state.report
        st.rerun()

if 'health_report' in st.session_state and st.session_state.health_report:
    st.header("💪 Phân tích sức khỏe")
    st.success(st.session_state.health_report)
    if st.button("🗑️ Xóa phân tích", key="clear_health"):
        del st.session_state.health_report
        st.rerun()

# --- Performance Metrics (in sidebar footer) ---
with st.sidebar:
    st.divider()
    st.caption("⚡ Performance Monitor")
    
    # Show cache stats if available
    if hasattr(assistant, 'response_cache'):
        cache_size = len(assistant.response_cache.cache)
        st.caption(f"📦 Cache: {cache_size} entries")
    
    # Memory usage hint
    if len(st.session_state.messages) > 20:
        st.caption("💡 Tip: Clear chat để tăng tốc độ")
        if st.button("🧹 Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

# --- Footer ---
st.divider()
st.caption("🚀 Optimized Personal AI Assistant v2.0 - Powered by RAG + Caching + Lazy Loading")