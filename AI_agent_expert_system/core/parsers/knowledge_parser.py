"""
知識庫解析器
將 Knowledge Base 文件拆解為百科式的知識卡片
"""

from typing import List, Dict
import logging
from .base_parser import BaseParser

logger = logging.getLogger(__name__)


class KnowledgeParser(BaseParser):
    """知識庫解析器 - 拆解為百科式的知識卡片"""
    
    def parse(self, chapters_data: Dict[str, str]) -> List[Dict]:
        """
        將知識庫的每個章節拆解為結構化的知識卡片
        
        Args:
            chapters_data: 章節字典 {"章節標題": "章節內容", ...}
        
        Returns:
            List[Dict]: 結構化的知識卡片列表
                [
                    {'type': 'chapter', 'title': '章節名', 'content': '結構化內容'},
                    ...
                ]
        """
        logger.info(f"開始解析 Knowledge 文件,共 {len(chapters_data)} 個章節...")
        
        chunks = []
        
        for chapter_title, chapter_content in chapters_data.items():
            # 構建 AI 分析 Prompt
            prompt = f"""請將以下內容轉換為結構化的知識卡片,包含以下 5 個部分:

1. Topic (主題) - 明確的主題名稱
2. Definition (定義) - 精簡的定義 (1-2句話)
3. Core Content (核心內容) - 詳細的技術細節、公式、流程說明
4. Key Terms (關鍵術語) - 列舉 3-5 個關鍵字
5. Examples (應用範例) - 實際應用場景或範例

請以以下 JSON 格式回傳:
{{
    "Topic": "...",
    "Definition": "...",
    "Core Content": "...",
    "Key Terms": "術語1, 術語2, 術語3",
    "Examples": "..."
}}

章節標題: {chapter_title}
章節內容:
{chapter_content}
"""
            
            try:
                # 呼叫 AI 分析
                response = self.ai_core.analyze_slide(prompt, api_mode="text_only")
                
                # 提取 JSON
                structured = self.extract_json_from_response(response)
                
                # 組合所有欄位為完整內容
                full_content = f"""主題: {structured.get('Topic', chapter_title)}

定義: {structured.get('Definition', '')}

核心內容:
{structured.get('Core Content', '')}

關鍵術語: {structured.get('Key Terms', '')}

應用範例:
{structured.get('Examples', '')}
"""
                
                chunks.append({
                    'type': 'chapter',
                    'title': chapter_title,
                    'content': full_content.strip()
                })
                
            except Exception as e:
                logger.warning(f"⚠️ 章節 '{chapter_title}' 解析失敗: {e},使用原始內容")
                # 解析失敗時,使用原始內容
                chunks.append({
                    'type': 'chapter',
                    'title': chapter_title,
                    'content': chapter_content
                })
        
        # 驗證切片
        validated_chunks = self.validate_chunks(chunks)
        
        logger.info(f"✅ Knowledge 解析完成,產生 {len(validated_chunks)} 個切片")
        return validated_chunks


if __name__ == "__main__":
    print("KnowledgeParser 定義完成")
