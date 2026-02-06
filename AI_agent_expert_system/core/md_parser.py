"""
AI Expert System - Markdown Parser Module
解析 Markdown 檔案，將標題視為分頁點
"""

import logging
import os
from typing import List, Dict

logger = logging.getLogger(__name__)

def parse_md(file_path: str) -> List[Dict]:
    """
    解析 MD 檔案
    
    Args:
        file_path: MD 檔案路徑
    
    Returns:
        List[Dict]: 模擬投影片資料列表
        格式: [
            {
                'page_num': 1,
                'text': '...',
                'images': []
            },
            ...
        ]
    """
    logger.info(f"開始解析 MD: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        slides_data = []
        current_text = []
        page_num = 1
        
        for line in lines:
            stripped = line.strip()
            # 遇到一級或二級標題，視為新的一頁 (若當前頁已有內容)
            if (stripped.startswith('# ') or stripped.startswith('## ')) and current_text:
                # 儲存上一頁
                # 檢查上一頁是否只有空行
                content = "".join(current_text).strip()
                if content:
                    slides_data.append({
                        'page_num': page_num,
                        'text': content,
                        'images': []
                    })
                    page_num += 1
                current_text = []
            
            current_text.append(line)
            
        # 儲存最後一頁
        if current_text:
            content = "".join(current_text).strip()
            if content:
                slides_data.append({
                    'page_num': page_num,
                    'text': content,
                    'images': []
                })
            
        logger.info(f"✅ 解析完成: {len(slides_data)} 頁 (MD章節), 檔案: {os.path.basename(file_path)}")
        return slides_data
        
    except Exception as e:
        logger.error(f"❌ MD 解析失敗: {file_path}, 錯誤: {e}")
        # 若發生錯誤，嘗試返回全文當作一頁
        try:
             with open(file_path, 'r', encoding='utf-8') as f:
                return [{
                    'page_num': 1,
                    'text': f.read(),
                    'images': []
                }]
        except:
             return []

# 測試用
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        result = parse_md(test_file)
        print(f"解析結果: {len(result)} 段落")
        for slide in result[:3]:
            print(f"\n段落 {slide['page_num']}:")
            print(f"  內容預覽: {slide['text'][:100]}...")
    else:
        print("使用方式: python md_parser.py <file_path>")
