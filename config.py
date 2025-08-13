# config_optimized.py

import os

# Model settings
OLLAMA_MODEL = 'llama3.2:3b'  # Updated default
EMBEDDING_MODEL = 'keepitreal/vietnamese-sbert'

# Alternative lighter embedding models (uncomment to try)
# EMBEDDING_MODEL = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'  # Lighter
# EMBEDDING_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'  # Fastest

# Vector DB settings
DB_PATH = "./diary_db"
DB_COLLECTION_NAME = "daily_diary"

# RAG settings - Dynamic based on DB size
N_RESULTS_RETRIEVAL = 3  # Will be overridden by dynamic calculation

# Performance settings
ENABLE_RESPONSE_CACHE = True
CACHE_TTL = 3600  # 1 hour
MAX_CACHE_SIZE = 100

ENABLE_LAZY_LOADING = True
ENABLE_ASYNC_PERSIST = True

# Model-specific optimizations
MODEL_CONFIGS = {
    'llama3.2:3b': {
        'optimal_temperature': 0.3,
        'optimal_top_p': 0.9,
        'optimal_top_k': 20,
        'max_tokens': 512,
        'context_window': 2048
    },
    'gemma2:2b': {
        'optimal_temperature': 0.4,
        'optimal_top_p': 0.8,
        'optimal_top_k': 15,
        'max_tokens': 256,
        'context_window': 1024
    },
    'qwen3:4b': {
        'optimal_temperature': 0.6,
        'optimal_top_p': 0.95,
        'optimal_top_k': 30,
        'max_tokens': 512,
        'context_window': 2048
    }
}

# Prompt templates optimized for specific tasks
PROMPT_TEMPLATES = {
    'diary_analysis': """Phân tích nhật ký và trả về JSON:
{
  "mood": "cảm xúc chính",
  "activities": ["hoạt động"],
  "health_notes": "ghi chú sức khỏe"
}

Nhật ký: {content}
JSON:""",
    
    'meal_planning': """Tạo thực đơn 1 ngày với JSON format:
{
  "breakfast": {"food": "tên món", "calories": 400},
  "lunch": {"food": "tên món", "calories": 600},
  "dinner": {"food": "tên món", "calories": 500},
  "total_calories": 1500
}

Yêu cầu: {requirements}
JSON:""",
    
    'workout_plan': """Tạo lịch tập với JSON:
{
  "exercises": [
    {"name": "tên bài tập", "sets": 3, "reps": 12, "rest": "60s"}
  ],
  "duration": "45 phút",
  "difficulty": "beginner/intermediate/advanced"
}

Mục tiêu: {goal}
JSON:""",
    
    'general_chat': """Bạn là trợ lý AI cá nhân. Dựa vào context từ nhật ký, trả lời ngắn gọn và hữu ích.

Context: {context}
Câu hỏi: {question}
Trả lời:"""
}

# Streamlit settings
STREAMLIT_CONFIG = {
    'page_title': 'Trợ lý AI Cá nhân',
    'layout': 'wide',
    'initial_sidebar_state': 'expanded'
}

# Debug settings
DEBUG_MODE = os.getenv('DEBUG', 'False').lower() == 'true'
VERBOSE_LOGGING = os.getenv('VERBOSE', 'False').lower() == 'true'

def get_model_config(model_name: str) -> dict:
    """Get optimized config for specific model"""
    for model_key, config in MODEL_CONFIGS.items():
        if model_key in model_name.lower():
            return config
    
    # Default config
    return {
        'optimal_temperature': 0.7,
        'optimal_top_p': 0.8, 
        'optimal_top_k': 20,
        'max_tokens': 512,
        'context_window': 2048
    }

def get_prompt_template(task_type: str) -> str:
    """Get optimized prompt template for task"""
    return PROMPT_TEMPLATES.get(task_type, PROMPT_TEMPLATES['general_chat'])