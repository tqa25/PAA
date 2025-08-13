# test_performance.py

import time
import asyncio
from rag_engine import OptimizedPersonalAssistant
import config as config

class PerformanceTest:
    def __init__(self, model_name="llama3.2:3b"):
        self.model_name = model_name
        self.assistant = None
        self.results = {}
    
    def setup(self):
        """Initialize assistant"""
        print(f"[SETUP] Initializing {self.model_name}...")
        start_time = time.time()
        
        self.assistant = OptimizedPersonalAssistant(
            model_name=self.model_name,
            temperature=0.3,
            top_p=0.9,
            top_k=20,
            presence_penalty=1.2
        )
        
        setup_time = time.time() - start_time
        self.results['setup_time'] = setup_time
        print(f"[SETUP] Complete in {setup_time:.2f}s")
    
    def test_cold_start(self):
        """Test first query (cold start)"""
        print("[TEST] Cold start query...")
        start_time = time.time()
        
        response = self.assistant.query("Xin chào! Bạn có thể giúp gì cho tôi?")
        
        cold_start_time = time.time() - start_time
        self.results['cold_start'] = cold_start_time
        print(f"[RESULT] Cold start: {cold_start_time:.2f}s")
        print(f"[RESPONSE] {response[:100]}...")
    
    def test_warm_queries(self):
        """Test subsequent queries (warm)"""
        print("[TEST] Warm queries...")
        
        queries = [
            "Tôi cảm thấy hôm nay rất tốt",
            "Gợi ý bữa sáng healthy cho tôi",
            "Làm thế nào để tăng năng suất làm việc?",
            "Tạo lịch tập gym cho người mới",
            "Phân tích tâm trạng tuần này"
        ]
        
        warm_times = []
        
        for i, query in enumerate(queries):
            start_time = time.time()
            response = self.assistant.query(query)
            query_time = time.time() - start_time
            warm_times.append(query_time)
            
            print(f"[WARM {i+1}] {query_time:.2f}s - {query[:30]}...")
        
        avg_warm_time = sum(warm_times) / len(warm_times)
        self.results['warm_queries'] = warm_times
        self.results['avg_warm_time'] = avg_warm_time
        print(f"[RESULT] Average warm time: {avg_warm_time:.2f}s")
    
    def test_cache_hit(self):
        """Test cache performance"""
        print("[TEST] Cache hit performance...")
        
        query = "Tôi cảm thấy hôm nay rất tốt"
        
        # First query (cache miss)
        start_time = time.time()
        response1 = self.assistant.query(query)
        miss_time = time.time() - start_time
        
        # Second query (cache hit)
        start_time = time.time()
        response2 = self.assistant.query(query)
        hit_time = time.time() - start_time
        
        speedup = miss_time / hit_time if hit_time > 0 else float('inf')
        
        self.results['cache_miss'] = miss_time
        self.results['cache_hit'] = hit_time
        self.results['cache_speedup'] = speedup
        
        print(f"[RESULT] Cache miss: {miss_time:.2f}s")
        print(f"[RESULT] Cache hit: {hit_time:.2f}s")
        print(f"[RESULT] Speedup: {speedup:.1f}x")
    
    def test_diary_processing(self):
        """Test diary entry processing"""
        print("[TEST] Diary processing...")
        
        diary_content = """
        Hôm nay tôi dậy lúc 6h30, cảm thấy khá tươi tỉnh. 
        Ăn sáng phở bò, uống cà phê đen. 
        Làm việc từ 8h đến 17h, có họp team lúc 14h.
        Tập gym 45 phút, chạy bộ 3km.
        Ăn tối với gia đình, xem phim Netflix.
        Đi ngủ lúc 22h30, cảm thấy hài lòng với ngày hôm nay.
        """
        
        start_time = time.time()
        result = self.assistant.add_diary_entry(diary_content, "2024-08-04")
        processing_time = time.time() - start_time
        
        self.results['diary_processing'] = processing_time
        print(f"[RESULT] Diary processing: {processing_time:.2f}s")
        print(f"[RESPONSE] {result}")
    
    def test_memory_usage(self):
        """Test memory usage (if psutil available)"""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            self.results['memory_usage_mb'] = memory_mb
            print(f"[RESULT] Memory usage: {memory_mb:.1f} MB")
            
        except ImportError:
            print("[SKIP] psutil not available, skipping memory test")
    
    def run_all_tests(self):
        """Run complete test suite"""
        print("="*60)
        print(f"PERFORMANCE TEST SUITE - {self.model_name}")
        print("="*60)
        
        self.setup()
        self.test_cold_start()
        self.test_warm_queries()
        self.test_cache_hit()
        self.test_diary_processing()
        self.test_memory_usage()
        
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("PERFORMANCE SUMMARY")
        print("="*60)
        
        print(f"Model: {self.model_name}")
        print(f"Setup time: {self.results.get('setup_time', 0):.2f}s")
        print(f"Cold start: {self.results.get('cold_start', 0):.2f}s")
        print(f"Average warm query: {self.results.get('avg_warm_time', 0):.2f}s")
        print(f"Cache speedup: {self.results.get('cache_speedup', 0):.1f}x")
        print(f"Diary processing: {self.results.get('diary_processing', 0):.2f}s")
        
        if 'memory_usage_mb' in self.results:
            print(f"Memory usage: {self.results['memory_usage_mb']:.1f} MB")
        
        # Performance rating
        avg_time = self.results.get('avg_warm_time', 999)
        if avg_time < 2.0:
            rating = "🚀 Excellent"
        elif avg_time < 5.0:
            rating = "✅ Good"
        elif avg_time < 10.0:
            rating = "⚠️ Acceptable"
        else:
            rating = "❌ Needs optimization"
        
        print(f"Overall rating: {rating}")
        print("="*60)

def compare_models():
    """Compare multiple models"""
    models = ["llama3.2:3b", "gemma2:2b"]  # Add more models as needed
    
    for model in models:
        try:
            test = PerformanceTest(model)
            test.run_all_tests()
            print("\n" + "-"*60 + "\n")
        except Exception as e:
            print(f"[ERROR] Failed to test {model}: {e}")

if __name__ == "__main__":
    # Test single model
    test = PerformanceTest("llama3.2:3b")
    test.run_all_tests()
    
    # Uncomment to compare multiple models
    # compare_models()