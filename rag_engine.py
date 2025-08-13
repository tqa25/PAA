# rag_engine_optimized.py

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
import langchain
import hashlib
import threading
from functools import lru_cache
from typing import Dict, List, Optional
import time

class OptimizedVietSBERTEncoder:
    """Optimized wrapper cho SentenceTransformer với caching và lazy loading."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, model_name):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, model_name):
        if not self._initialized:
            print(f"[INIT] Loading embedding model: {model_name}")
            self.model = SentenceTransformer(model_name)
            self._cache = {}
            self._cache_max_size = 1000
            self._initialized = True
    
    @lru_cache(maxsize=500)
    def embed_query(self, text: str):
        """Cache embed_query results"""
        return self.model.encode([text])[0].tolist()
    
    def embed_documents(self, texts: List[str]):
        """Batch embedding with caching"""
        results = []
        for text in texts:
            text_hash = hashlib.md5(text.encode()).hexdigest()[:16]
            if text_hash in self._cache:
                results.append(self._cache[text_hash])
            else:
                embedding = self.model.encode([text])[0].tolist()
                if len(self._cache) < self._cache_max_size:
                    self._cache[text_hash] = embedding
                results.append(embedding)
        return results

class ResponseCache:
    """Simple in-memory response cache"""
    
    def __init__(self, max_size: int = 100, ttl: int = 3600):
        self.cache = {}
        self.max_size = max_size
        self.ttl = ttl
        self._lock = threading.Lock()
    
    def _generate_key(self, question: str, model_name: str, params: dict) -> str:
        """Generate cache key from question and parameters"""
        param_str = json.dumps(params, sort_keys=True)
        content = f"{question}|{model_name}|{param_str}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, question: str, model_name: str, params: dict) -> Optional[str]:
        """Get cached response if available and not expired"""
        key = self._generate_key(question, model_name, params)
        with self._lock:
            if key in self.cache:
                response, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl:
                    print(f"[CACHE] Cache hit for question: {question[:50]}...")
                    return response
                else:
                    del self.cache[key]
        return None
    
    def set(self, question: str, model_name: str, params: dict, response: str):
        """Cache response"""
        key = self._generate_key(question, model_name, params)
        with self._lock:
            if len(self.cache) >= self.max_size:
                # Remove oldest entry
                oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
                del self.cache[oldest_key]
            
            self.cache[key] = (response, time.time())

class OptimizedPersonalAssistant:
    """
    Optimized version của PersonalAssistant với performance improvements
    """
    
    def __init__(self, model_name: str, temperature: float = 0.7, 
                 top_p: float = 0.8, top_k: int = 20, presence_penalty: float = 1.5):
        
        print(f"[INIT] Initializing assistant with model: {model_name}")
        
        self.model_name = model_name
        self.model_params = {
            'temperature': temperature,
            'top_p': top_p, 
            'top_k': top_k,
            'presence_penalty': presence_penalty
        }
        
        # Initialize response cache
        self.response_cache = ResponseCache()
        
        # Lazy loading for heavy components
        self._llm = None
        self._encoder = None
        self._vector_store = None
        self._rag_chain = None
        
        print("[INIT] Assistant initialized (lazy loading enabled)")
    
    @property
    def encoder(self):
        """Lazy load encoder"""
        if self._encoder is None:
            self._encoder = OptimizedVietSBERTEncoder(config.EMBEDDING_MODEL)
        return self._encoder
    
    @property
    def llm(self):
        """Lazy load LLM"""
        if self._llm is None:
            print(f"[LAZY] Loading LLM: {self.model_name}")
            self._llm = Ollama(
                model=self.model_name,
                temperature=self.model_params['temperature'],
                top_k=self.model_params['top_k'],
                top_p=self.model_params['top_p'],
                repeat_penalty=self.model_params['presence_penalty']
            )
        return self._llm
    
    @property
    def vector_store(self):
        """Lazy load vector store"""
        if self._vector_store is None:
            print("[LAZY] Loading vector store")
            self._vector_store = Chroma(
                collection_name=config.DB_COLLECTION_NAME,
                embedding_function=self.encoder,
                persist_directory=config.DB_PATH,
            )
        return self._vector_store
    
    @property
    def rag_chain(self):
        """Lazy load RAG chain"""
        if self._rag_chain is None:
            print("[LAZY] Setting up RAG chain")
            self._setup_rag_chain()
        return self._rag_chain
    
    def _setup_rag_chain(self):
        """Setup optimized RAG chain"""
        
        # Optimized prompt template
        prompt_template = """Bạn là trợ lý AI cá nhân thông minh. Dựa vào context từ nhật ký, trả lời câu hỏi bằng tiếng Việt một cách tự nhiên và hữu ích.

Context: {context}

Câu hỏi: {question}

Trả lời:"""
        
        prompt = PromptTemplate(
            template=prompt_template, 
            input_variables=["context", "question"]
        )
        
        # Dynamic retrieval based on question type
        self._rag_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vector_store.as_retriever(
                search_kwargs={"k": self._get_optimal_k()}
            ),
            chain_type_kwargs={"prompt": prompt},
            return_source_documents=False  # Reduce memory usage
        )
    
    def _get_optimal_k(self) -> int:
        """Dynamic k based on DB size"""
        try:
            collection = self.vector_store._collection
            count = collection.count()
            if count < 5:
                return min(count, 2)
            elif count < 20:
                return 3
            else:
                return 4
        except:
            return 3
    
    def _extract_info_from_diary_optimized(self, content: str) -> dict:
        """Optimized diary info extraction with structured prompt"""
        
        # Check cache first
        content_hash = hashlib.md5(content.encode()).hexdigest()[:16]
        cache_key = f"extract_{content_hash}"
        
        if hasattr(self, '_extraction_cache') and cache_key in self._extraction_cache:
            return self._extraction_cache[cache_key]
        
        # Structured prompt for better JSON extraction
        prompt = f"""Phân tích nhật ký và trả về JSON chính xác:

{{
  "mood": "vui vẻ/buồn/bình thường/căng thẳng/hạnh phúc",
  "activities": ["hoạt động 1", "hoạt động 2"],
  "key_events": ["sự kiện quan trọng"],
  "health_notes": "ghi chú về sức khỏe nếu có"
}}

Nhật ký: {content}

JSON:"""
        
        try:
            response = self.llm.invoke(prompt)
            
            # Better JSON extraction
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                
                # Cache result
                if not hasattr(self, '_extraction_cache'):
                    self._extraction_cache = {}
                if len(self._extraction_cache) < 50:  # Limit cache size
                    self._extraction_cache[cache_key] = result
                
                return result
            
        except Exception as e:
            print(f"[ERROR] Extraction failed: {e}")
        
        # Fallback
        return {
            "mood": "Không xác định", 
            "activities": [],
            "key_events": [],
            "health_notes": ""
        }
    
    def add_diary_entry(self, content: str, date: str = None) -> str:
        """Optimized diary entry addition"""
        if not date:
            date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        print(f"[DIARY] Processing entry for {date}")
        
        # Extract info with optimization
        extracted_info = self._extract_info_from_diary_optimized(content)
        
        metadata = {
            "date": date,
            "type": "diary_entry",
            "mood": extracted_info.get("mood", "Không xác định"),
            "activities": ", ".join(extracted_info.get("activities", [])),
            "key_events": ", ".join(extracted_info.get("key_events", [])),
            "health_notes": extracted_info.get("health_notes", "")
        }
        
        # Use date as ID to prevent duplicates
        self.vector_store.add_texts(
            texts=[content],
            metadatas=[metadata],
            ids=[f"diary_{date}"]
        )
        
        # Async persist (non-blocking)
        threading.Thread(target=self.vector_store.persist, daemon=True).start()
        
        return f"✅ Đã lưu nhật ký ngày {date}"
    
    def add_knowledge_document(self, content: str, source: str) -> str:
        """Optimized knowledge document addition"""
        print(f"[KNOWLEDGE] Adding document from: {source}")
        
        metadata = {
            "source": source,
            "import_date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "type": "knowledge_document",
            "content_length": len(content)
        }
        
        # Generate stable ID
        doc_id = f"knowledge_{hashlib.md5((source + content).encode()).hexdigest()[:16]}"
        
        self.vector_store.add_texts(
            texts=[content],
            metadatas=[metadata], 
            ids=[doc_id]
        )
        
        # Async persist
        threading.Thread(target=self.vector_store.persist, daemon=True).start()
        
        return f"✅ Đã lưu kiến thức từ '{source}'"
    
    def query(self, question: str, thinking_mode: bool = False, debug_mode: bool = False) -> str:
        """Optimized query with caching and performance monitoring"""
        
        start_time = time.time()
        print(f"[QUERY] Processing: '{question[:50]}...'")
        
        # Check cache first
        cache_params = {
            'thinking_mode': thinking_mode,
            'debug_mode': debug_mode,
            **self.model_params
        }
        
        cached_response = self.response_cache.get(question, self.model_name, cache_params)
        if cached_response:
            print(f"[PERF] Cache hit, response time: {time.time() - start_time:.2f}s")
            return cached_response
        
        # Set debug mode
        langchain.debug = debug_mode
        
        try:
            # Process question
            final_question = question
            if "qwen3" in self.model_name.lower():
                suffix = " /think" if thinking_mode else " /no_think"
                final_question = f"{question}{suffix}"
            
            # Execute RAG chain
            result = self.rag_chain.invoke({"query": final_question})
            response_text = result['result']
            
            # Clean thinking tags
            if "<think>" in response_text:
                parts = response_text.split("</think>", 1)
                if len(parts) > 1:
                    response_text = parts[1].strip()
            
            # Cache response
            self.response_cache.set(question, self.model_name, cache_params, response_text)
            
            elapsed = time.time() - start_time
            print(f"[PERF] Query completed in {elapsed:.2f}s")
            
            return response_text.strip()
            
        except Exception as e:
            print(f"[ERROR] Query failed: {e}")
            return f"Xin lỗi, có lỗi xảy ra: {str(e)}"
        
        finally:
            langchain.debug = False
    
    def get_daily_summary_and_plan(self) -> str:
        """Optimized daily summary with structured prompt"""
        
        prompt = """Dựa trên nhật ký gần đây, tạo báo cáo ngắn gọn:

1. Tóm tắt tuần qua (2-3 câu)
2. Điểm mạnh cần duy trì
3. 3 gợi ý cụ thể cho ngày mai

Trả lời trong 150 từ."""
        
        return self.query(prompt, thinking_mode=False, debug_mode=False)
    
    def get_health_insights(self) -> str:
        """New feature: Health insights from diary"""
        
        prompt = """Phân tích các ghi chú sức khỏe trong nhật ký và đưa ra:
1. Patterns về giấc ngủ, ăn uống, vận động
2. Xu hướng tâm trạng
3. Khuyến nghị cải thiện sức khỏe

Trả lời trong 100 từ."""
        
        return self.query(prompt, thinking_mode=False, debug_mode=False)

# Compatibility alias
PersonalAssistant = OptimizedPersonalAssistant