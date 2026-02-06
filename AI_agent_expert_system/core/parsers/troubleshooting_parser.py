"""
異常報告解析器
將 Troubleshooting 文件標準化為 6 大欄位
"""

from typing import List, Dict
import logging
from .base_parser import BaseParser

logger = logging.getLogger(__name__)


class TroubleshootingParser(BaseParser):
    """異常報告解析器 - 標準化為 6 大欄位"""
    
    # 標準欄位定義
    STANDARD_FIELDS = [
        "Problem issue & loss",
        "Problem description",
        "Analysis root cause",
        "Containment action",
        "Corrective action",
        "Preventive action"
    ]
    
    def parse(self, raw_data: str) -> List[Dict]:
        """
        將異常報告解析為 6 個標準欄位
        
        Args:
            raw_data: 原始文件內容 (字串)
        
        Returns:
            List[Dict]: 6 個標準欄位的切片
                [
                    {'type': 'field', 'title': 'Problem issue & loss', 'content': '...'},
                    {'type': 'field', 'title': 'Problem description', 'content': '...'},
                    ...
                ]
        """
        logger.info("開始解析 Troubleshooting 文件...")
        
        # 構建 AI 分析 Prompt
        prompt = f"""你是一位專業的品質工程師。請分析以下異常報告,並將內容歸納為以下 6 個標準欄位。
若原始資料中缺少某些欄位,請根據上下文合理推斷。

標準欄位:
1. Problem issue & loss (問題議題與損失)
2. Problem description (問題描述)
3. Analysis root cause (根本原因分析)
4. Containment action (圍堵對策)
5. Corrective action (矯正對策)
6. Preventive action (預防對策)

請以以下 JSON 格式回傳:
{{
    "Problem issue & loss": "...",
    "Problem description": "...",
    "Analysis root cause": "...",
    "Containment action": "...",
    "Corrective action": "...",
    "Preventive action": "..."
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
            for field in self.STANDARD_FIELDS:
                content = extracted.get(field, "未提供")
                chunks.append({
                    'type': 'field',
                    'title': field,
                    'content': content
                })
            
            # 驗證切片
            validated_chunks = self.validate_chunks(chunks)
            
            logger.info(f"✅ Troubleshooting 解析完成,產生 {len(validated_chunks)} 個切片")
            return validated_chunks
            
        except Exception as e:
            logger.error(f"❌ Troubleshooting 解析失敗: {e}")
            # 回傳空列表或基本結構
            return [
                {
                    'type': 'field',
                    'title': '原始內容',
                    'content': raw_data[:500] + "..." if len(raw_data) > 500 else raw_data
                }
            ]


if __name__ == "__main__":
    print("TroubleshootingParser 定義完成")
