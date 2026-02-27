
import sys
import os
import logging

# 設定 logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 確保可以匯入 core 模組
# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import find_document_by_metadata

def test_retrieval():
    print("開始測試 Metadata 精確檢索...")
    
    # 測試案例 1: 應該存在的資料
    # 根據之前的 log，我們知道有 N706 Oven Pin 的資料 (雖然之前解析失敗，但在資料庫中應該有 metadata)
    # 或者 N706 蝴蝶Mura (這是解析成功的)
    
    product = "N706"
    defect = "蝴蝶Mura"
    
    print(f"\n[測試 1] 尋找 Product={product}, Defect={defect}")
    result = find_document_by_metadata(product, defect)
    
    if result:
        print("✅ 找到文件!")
        print(f"  - Filename: {result['filename']}")
        print(f"  - Doc ID: {result['doc_id']}")
        print(f"  - Metadata: {result['metadata']}")
        print(f"  - Content Length: {len(result['content'])} chars")
    else:
        print("❌ 未找到文件 (可能是 metadata 不匹配)")
        
    # 測試案例 2: 不存在的資料
    product_fake = "N999"
    defect_fake = "不存在的缺陷"
    
    print(f"\n[測試 2] 尋找 Product={product_fake}, Defect={defect_fake}")
    result_fake = find_document_by_metadata(product_fake, defect_fake)
    
    if result_fake is None:
        print("✅ 正確回傳 None")
    else:
        print(f"❌ 錯誤: 竟然找到了 {result_fake['filename']}")

if __name__ == "__main__":
    test_retrieval()
