import sqlite3
import os
import sys
import io

# 強制使用 UTF-8輸出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 資料庫路徑
# 資料庫路徑
# 使用相對路徑，假設 tests 目錄在 AI_agent_expert_system 下
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "knowledge.db")

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_failed_chunks():
    if not os.path.exists(DB_PATH):
        print(f"資料庫不存在: {DB_PATH}")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print(f"正在查詢資料庫: {DB_PATH}")
        
        # 1. 查詢所有 Troubleshooting 文件的解析狀態
        query = """
        SELECT d.id, d.filename, c.source_title, c.text_content, c.source_type
        FROM vec_chunks c 
        JOIN documents d ON c.doc_id = d.id 
        WHERE d.doc_type = 'Troubleshooting'
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        if not results:
            print("❌ 資料庫中沒有 Troubleshooting 文件記錄")
        else:
            print(f"📊 總共找到 {len(results)} 個 Troubleshooting 切片紀錄:\n")
            
            failed_count = 0
            success_count = 0
            
            for row in results:
                doc_id, file_name, title, content, source_type = row
                
                # 判斷是否為失敗的解析 (標題包含 '原始內容' 或 source_type 不正確)
                is_failed = '原始內容' in title or source_type != 'troubleshooting_full'
                
                if is_failed:
                    failed_count += 1
                    status = "❌ 解析失敗 (未生成 8D 格式)"
                else:
                    success_count += 1
                    status = "✅ 解析成功 (8D 格式)"
                
                print(f"[ID: {doc_id}] {file_name}")
                print(f"  狀態: {status}")
                print(f"  標題: {title}")
                print(f"  類型: {source_type}")
                print("-" * 50)
                
                # 如果是失敗的文件 (ID 4), 將內容匯出以便分析
                if is_failed:
                    try:
                        with open("failed_content.txt", "w", encoding="utf-8") as f:
                            f.write(content)
                        print(f"⚠️ 已將失敗文件內容匯出至 failed_content.txt")
                    except Exception as e:
                        print(f"匯出失敗: {e}")
            
            print(f"\n統計結果:")
            print(f"✅ 成功: {success_count}")
            print(f"❌ 失敗: {failed_count}")
                
        conn.close()
        
    except Exception as e:
        print(f"查詢失敗: {e}")

if __name__ == "__main__":
    check_failed_chunks()
