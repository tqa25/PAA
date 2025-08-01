# config.py

# Model settings
# Giá trị này sẽ được ghi đè bởi lựa chọn trên giao diện, nhưng vẫn cần cho lần chạy đầu
OLLAMA_MODEL = 'qwen:4b' 
EMBEDDING_MODEL = 'keepitreal/vietnamese-sbert'

# Vector DB settings
DB_PATH = "./diary_db"
DB_COLLECTION_NAME = "daily_diary"

# RAG settings
# Số lượng kết quả tìm kiếm liên quan để đưa vào context cho LLM
N_RESULTS_RETRIEVAL = 3 