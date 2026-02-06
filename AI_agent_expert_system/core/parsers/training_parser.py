"""
教育訓練解析器
將 Training 文件標準化為 5 大教學區塊
"""

from typing import List, Dict
import logging
from .base_parser import BaseParser

logger = logging.getLogger(__name__)


class TrainingParser(BaseParser):
    """教育訓練解析器 - 標準化為 5 大教學區塊"""
    
    # 標準區塊定義
    STANDARD_SECTIONS = [
        "Target Audience",
        "Learning Objectives",
        "Prerequisites",
        "Core Modules",
        "Quiz/Assessment"
    ]
    
    def parse(self, raw_data: str) -> List[Dict]:
        """
        將教育訓練文件解析為 5 大區塊
        
        Args:
            raw_data: 原始文件內容 (字串)
        
        Returns:
            List[Dict]: 5 個標準區塊的切片
                [
                    {'type': 'section', 'title': 'Target Audience', 'content': '...'},
                    {'type': 'section', 'title': 'Learning Objectives', 'content': '...'},
                    ...
                ]
        """
        logger.info("開始解析 Training 文件...")
        
        # 構建 AI 分析 Prompt
        prompt = f"""你是一位專業的企業講師。請將這份投影片教材重新組織為教學大綱,
必須包含以下五個部分:

1. Target Audience (適用對象) - 這門課適合誰?
2. Learning Objectives (學習目標) - 學員能學到什麼?
3. Prerequisites (先備知識) - 需要哪些前置知識?
4. Core Modules (核心單元) - 主要教學內容
5. Quiz/Assessment (課後測驗) - 考核重點

若原文件中缺乏某部分,請根據內容屬性進行合理推斷與歸納。

請以以下 JSON 格式回傳:
{{
    "Target Audience": "...",
    "Learning Objectives": "...",
    "Prerequisites": "...",
    "Core Modules": "...",
    "Quiz/Assessment": "..."
}}

原始內容:
{raw_data}
"""
        
        try:
            # 呼叫 AI 分析
            response = self.ai_core.analyze_slide(prompt, api_mode="text_only")
            
            # 提取 JSON
            extracted = self.extract_json_from_response(response)
            
            # 轉換為切片格式
            chunks = []
            for section in self.STANDARD_SECTIONS:
                content = extracted.get(section, "未提供")
                chunks.append({
                    'type': 'section',
                    'title': section,
                    'content': content
                })
            
            # 驗證切片
            validated_chunks = self.validate_chunks(chunks)
            
            logger.info(f"✅ Training 解析完成,產生 {len(validated_chunks)} 個切片")
            return validated_chunks
            
        except Exception as e:
            logger.error(f"❌ Training 解析失敗: {e}")
            # 回傳空列表或基本結構
            return [
                {
                    'type': 'section',
                    'title': '原始內容',
                    'content': raw_data[:500] + "..." if len(raw_data) > 500 else raw_data
                }
            ]


if __name__ == "__main__":
    print("TrainingParser 定義完成")
