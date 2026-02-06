import os
import sys
import logging
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database.connection import get_connection
from core.database import vector_ops
from core.database.schema import create_all_tables
from core.keyword_manager import get_keyword_manager

# 設定 logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def backfill_keywords():
    """
    回填關鍵字：
    1. 撈取 keywords 為空的 chunks
    2. 使用 KeywordManager 的關鍵字進行純文字比對
    3. 若有對應，更新資料庫
    """
    # 確保資料庫 Schema 正確 (包含 keywords 欄位)
    create_all_tables()
    
    logger.info("開始執行關鍵字回填 (String Matching Mode)...")
    
    # 1. 取得 KeywordManager 資料
    km = get_keyword_manager()
    all_mappings = km.get_all_data()
    
    keyword_count = sum(len(v) for v in all_mappings.values())
    logger.info(f"已載入 {len(all_mappings)} 個類別，共 {keyword_count} 個關鍵字")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 2. 撈取未處理的 chunks (keywords IS NULL OR keywords = '')
        cursor.execute("SELECT chunk_id, text_content FROM vec_chunks WHERE keywords IS NULL OR keywords = ''")
        chunks = cursor.fetchall()
        
        total_chunks = len(chunks)
        logger.info(f"找到 {total_chunks} 個待處理的切片")
        
        updated_count = 0
        
        for i, (chunk_id, content) in enumerate(chunks):
            if not content:
                continue
                
            categorized_keywords = []
            
            # 3. 進行字串比對
            for category, keyword_list in all_mappings.items():
                for kw in keyword_list:
                    # 使用 case-insensitive 比對? 
                    # 這裡先做簡單的 case-sensitive (若要忽略大小寫，可轉 .lower())
                    if kw in content:
                        categorized_keywords.append(f"{category}:{kw}")
            
            # 4. 若有找到關鍵字，更新 DB
            if categorized_keywords:
                # 去重
                categorized_keywords = list(set(categorized_keywords))
                keywords_str = ",".join(categorized_keywords)
                
                vector_ops.update_chunk_keywords(chunk_id, keywords_str)
                updated_count += 1
                logger.debug(f"Chunk {chunk_id} 更新: {keywords_str}")
            
            # 顯示進度
            if (i + 1) % 100 == 0:
                print(f"進度: {i + 1}/{total_chunks} (更新: {updated_count})", end='\r')
        
        print(f"\n回填完成！ 共更新 {updated_count}/{total_chunks} 個切片")
        
    except Exception as e:
        logger.error(f"執行失敗: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    backfill_keywords()
