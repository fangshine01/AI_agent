
import sys
import logging
import traceback
import io
import re
from unittest.mock import MagicMock

# 強制使用 UTF-8輸出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 設定 logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 模擬 AI Core
class MockAICore:
    def __init__(self, filename):
        self.filename = filename
        
    def analyze_slide(self, prompt, api_mode="text_only"):
        print(f"[Mock] AI Analyze called for {self.filename}")
        return """
        {
            "Problem issue & loss": "Test Issue",
            "Problem description": "Test Description",
            "Analysis root cause": "Test Root Cause",
            "Containment action": "Test Action",
            "Corrective action": ["Action 1", "Action 2"],
            "Preventive action": ["Prevention 1", "Prevention 2"],
            "product": "N706",
            "defect_code": "Oven Pin",
            "station": "INT",
            "yield_loss": "0.5%"
        }
        """

# 匯入 Parser
try:
    from core.parsers.troubleshooting_parser import TroubleshootingParser
except ImportError:
    from core.parsers.troubleshooting_parser import TroubleshootingParser

def simulate_parsing():
    filename = "N706 Oven Pin issue For INT 內部.pptx"
    # 嘗試讀取真實的失敗內容
    try:
        # 使用相對路徑讀取同目錄下的 failed_content.txt
        failed_content_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "failed_content.txt")
        with open(failed_content_path, "r", encoding="utf-8") as f:
            raw_content = f.read()
        print(f"已讀取 failed_content.txt ({len(raw_content)} chars)")
    except FileNotFoundError:
        raw_content = "模擬的檔案內容..."
        print("未找到 failed_content.txt, 使用預設內容")
    
    print(f"開始模擬解析: {filename}")
    
    try:
        # 1. 初始化 Parser
        ai_wrapper = MockAICore(filename)
        parser = TroubleshootingParser(ai_wrapper)
        
        # 2. 測試 clean_text 方法 (這就是之前出問題的地方)
        test_text = "Line 1\nLine 2\nLine 3"
        cleaned_text = parser.clean_text(test_text)
        print(f"\n[測試 clean_text]")
        print(f"輸入: {repr(test_text)}")
        print(f"輸出: {repr(cleaned_text)}")
        
        if "\n" not in cleaned_text:
            print("[FAIL] clean_text 移除了換行符號!")
        else:
            print("[PASS] clean_text 保留了換行符號")
            
        # 3. 執行解析
        chunks = parser.parse(raw_content)
        
        # 4. 檢查結果
        for chunk in chunks:
            print(f"\nChunk Type: {chunk['type']}")
            print(f"Title: {chunk['title']}")
            if chunk['title'] == '原始內容':
                print("[FAIL] 解析失敗 (回退到原始內容)")
            else:
                print("[PASS] 解析成功")
                print(f"Content Preview: {chunk['content'][:50]}...")
                
    except Exception:
        print("[ERROR] 發生未捕獲的例外:")
        traceback.print_exc()

if __name__ == "__main__":
    simulate_parsing()
