# rag_engine.py

import chromadb
from sentence_transformers import SentenceTransformer
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import Chroma
import config
import datetime
import json
import re
import langchain  # Thêm import langchain để điều khiển chế độ debug

class VietSBERTEncoder:
    """Wrapper cho SentenceTransformer để tương thích với LangChain."""
    def __init__(self, model_name):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts):
        return self.model.encode(texts).tolist()

    def embed_query(self, text):
        return self.model.encode([text])[0].tolist()

class PersonalAssistant:
    """
    Lõi xử lý của Trợ lý AI Cá nhân, tích hợp RAG và các tham số điều khiển LLM.
    """
    def __init__(self, model_name: str, temperature: float = 0.7, top_p: float = 0.8, top_k: int = 20, presence_penalty: float = 1.5):
        print(f"Khởi tạo trợ lý với model: {model_name}")
        print(f"Tham số: temp={temperature}, top_p={top_p}, top_k={top_k}, repeat_penalty (from presence)={presence_penalty}")
        
        self.model_name = model_name
        
        self.encoder = VietSBERTEncoder(config.EMBEDDING_MODEL)
        
        self.vector_store = Chroma(
            collection_name=config.DB_COLLECTION_NAME,
            embedding_function=self.encoder,
            persist_directory=config.DB_PATH,
        )
        
        # Lớp Ollama trong LangChain dùng `repeat_penalty` để kiểm soát sự lặp lại.
        self.llm = Ollama(
            model=self.model_name,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
            repeat_penalty=presence_penalty
        )
        
        self._setup_rag_chain()

    def _setup_rag_chain(self):
        prompt_template = """
        Bạn là một trợ lý AI cá nhân, thấu hiểu và chu đáo.
        Dựa vào những thông tin được trích xuất từ nhật ký của người dùng dưới đây, hãy trả lời câu hỏi của họ một cách tự nhiên và hữu ích bằng tiếng Việt.
        Nếu không có thông tin liên quan, hãy nói rằng bạn không tìm thấy thông tin trong nhật ký.

        Context từ nhật ký:
        {context}

        Câu hỏi:
        {question}

        Câu trả lời của bạn:
        """
        
        prompt = PromptTemplate(
            template=prompt_template, input_variables=["context", "question"]
        )
        
        self.rag_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vector_store.as_retriever(search_kwargs={"k": config.N_RESULTS_RETRIEVAL}),
            chain_type_kwargs={"prompt": prompt},
            return_source_documents=True
        )

    def _extract_info_from_diary(self, content):
        prompt = f"""
        Đọc đoạn nhật ký sau và trích xuất các thông tin: tâm trạng chính (mood), các hoạt động (activities) dưới dạng một danh sách các chuỗi.
        Chỉ trả về một đối tượng JSON hợp lệ, không giải thích gì thêm.
        Ví dụ: {{"mood": "Vui vẻ", "activities": ["Họp team", "Ăn tối với bạn bè", "Xem phim"]}}

        Nhật ký:
        {content}
        """
        try:
            response = self.llm.invoke(prompt)
            json_str = re.search(r'\{.*\}', response, re.DOTALL).group(0)
            return json.loads(json_str)
        except Exception as e:
            print(f"Lỗi khi trích xuất thông tin: {e}")
            return {"mood": "Không xác định", "activities": []}

    def add_diary_entry(self, content: str, date: str = None):
        if not date:
            date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        print("Đang trích xuất thông tin từ nhật ký...")
        extracted_info = self._extract_info_from_diary(content)
        
        metadata = {
            "date": date,
            "mood": extracted_info.get("mood", "Không xác định"),
            "activities": ", ".join(extracted_info.get("activities", []))
        }
        
        print(f"Đang thêm vào database với metadata: {metadata}")
        self.vector_store.add_texts(
            texts=[content],
            metadatas=[metadata],
            ids=[f"diary_{date}"]
        )
        self.vector_store.persist()
        return f"Đã lưu nhật ký ngày {date}."
    
    def add_knowledge_document(self, content: str, source: str):
        """
        Thêm một tài liệu kiến thức vào Vector DB.
        - content: Nội dung kiến thức.
        - source: Nguồn của kiến thức (ví dụ: "Tài liệu StarCoder2", "Wikipedia")
        """
        print(f"Đang thêm tài liệu kiến thức từ nguồn: {source}")
        
        # Metadata để phân biệt với nhật ký
        metadata = {
            "source": source,
            "import_date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "type": "knowledge_document" # Đây là key quan trọng để phân biệt
        }
        
        # Tạo một ID duy nhất cho tài liệu
        # Dùng hàm hash của Python để tạo ID từ nội dung
        doc_id = f"knowledge_{hash(content)}"

        self.vector_store.add_texts(
            texts=[content],
            metadatas=[metadata],
            ids=[doc_id]
        )
        self.vector_store.persist()
        return f"Đã lưu tài liệu kiến thức từ nguồn '{source}'."

    def query(self, question: str, thinking_mode: bool = False, debug_mode: bool = False):
        """
        Xử lý câu hỏi của người dùng.
        - thinking_mode: Bật chế độ /think của Qwen3.
        - debug_mode: Bật chế độ in log chi tiết của LangChain.
        """
        print(f"\n[INFO] Nhận câu hỏi mới: '{question}' | Thinking: {thinking_mode} | Debug: {debug_mode}")

        # Bật/tắt chế độ debug của LangChain
        langchain.debug = debug_mode
        
        final_question = question
        if "qwen3" in self.model_name.lower():
            if thinking_mode:
                final_question = f"{question} /think"
            else:
                final_question = f"{question} /no_think"

        # Gọi RAG chain để xử lý
        result = self.rag_chain.invoke({"query": final_question})
        
        # Tắt chế độ debug ngay sau khi chạy xong để không làm nhiễu các lần gọi khác
        langchain.debug = False

        # Xử lý kết quả trả về
        response_text = result['result']
        if "<think>" in response_text:
            parts = response_text.split("</think>", 1)
            if len(parts) > 1:
                return parts[1].strip()
        return response_text.strip()
    
    def get_daily_summary_and_plan(self):
        question = "Dựa trên các hoạt động và tâm trạng gần đây, hãy đưa ra một đánh giá ngắn gọn về tuần qua và gợi ý 3 điều cụ thể tôi nên tập trung vào ngày mai để hiệu quả và vui vẻ hơn."
        # Mặc định bật thinking mode, và có thể bật debug mode nếu muốn
        return self.query(question, thinking_mode=True, debug_mode=False)