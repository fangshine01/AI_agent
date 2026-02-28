"""
SOP (Procedure) Parser
用於解析標準作業程序文件,提取結構化資訊
"""

import logging
import json
from typing import List, Dict, Any
from .base_parser import BaseParser

logger = logging.getLogger(__name__)

class ProcedureParser(BaseParser):
    """SOP 解析器 - 專注於提取操作步驟與安全規範"""
    
    def parse(self, content: str) -> List[Dict[str, Any]]:
        """
        解析 SOP 內容
        
        Args:
            content: 原始文件內容 (文字)
        
        Returns:
            List[Dict]: 結構化的切片列表
        """
        logger.info("開始解析 Procedure 文件...")
        
        # 1. 構建 Prompt
        prompt = f"""你是一位標準作業程序 (SOP) 專家。請分析以下文件內容，並將其整理為結構化的 Markdown 操作手冊。

請重點提取以下資訊：
1. Goal (作業目標): 這份 SOP 的主要目的
2. Target (適用範圍): 適用於哪些機台、站點或製程
3. Tools (工具與耗材): 需要準備的工具、儀器或材料
4. Safety (安全注意事項): 任何危險警告、禁止事項或防護裝備要求 (請用 ⚠️ 標示)
5. Steps (詳細步驟): 請按順序條列操作步驟，確保邏輯清晰。若有子步驟請縮排。

請以 JSON 格式回傳，欄位如下：
{{
    "Goal": "...",
    "Target": "...",
    "Tools": ["工具1", "工具2"],
    "Safety": ["注意1", "注意2"],
    "Steps": ["1. 步驟一...", "2. 步驟二..."]
}}

文件內容:
{content[:15000]}
"""
        
        try:
            # 2. 呼叫 AI (使用 text_only 模式, 因為此處通常處理 OCR 後的文字)
            # 若需 Vision 已在 Ingestion 層處理圖片轉文字
            response = self.ai_core.analyze_slide(prompt, api_mode="text_only")
            
            # 3. 提取 JSON
            structured_data = self.extract_json_from_response(response)
            
            if not structured_data:
                logger.warning("SOP 解析未能產生結構化資料, 使用原始內容")
                return [{
                    'type': 'raw',
                    'title': 'SOP 原始內容',
                    'content': content
                }]

            # 4. 轉為 Markdown 格式 (用於直讀)
            md_content = self._generate_markdown(structured_data)
            
            # 5. 回傳單一切片 (SOP 通常作為整體檢索)
            return [{
                'type': 'procedure_full',
                'title': structured_data.get('Goal', '標準作業程序'),
                'content': md_content,
                'metadata': structured_data
            }]
            
        except Exception as e:
            logger.error(f"SOP 解析失敗: {e}")
            # Fallback: 回傳原始內容
            return [{
                'type': 'raw',
                'title': 'SOP 原始內容',
                'content': content
            }]

    def _generate_markdown(self, data: Dict) -> str:
        """生成標準化的 Markdown"""
        md = []
        
        # Goal (Title)
        goal = data.get('Goal', '標準作業程序')
        md.append(f"# [SOP] {goal}")
        
        # Target
        if data.get('Target'):
            md.append(f"\n## 🎯 適用範圍\n{data['Target']}")
        
        # Safety (High Priority)
        if data.get('Safety'):
            md.append(f"\n## ⚠️ 安全注意事項")
            for item in data['Safety']:
                md.append(f"- {item}")
        
        # Tools
        if data.get('Tools'):
            md.append(f"\n## 🛠️ 準備工具")
            for item in data['Tools']:
                md.append(f"- {item}")
        
        # Steps
        if data.get('Steps'):
            md.append(f"\n## 🔢 操作步驟")
            for step in data['Steps']:
                md.append(f"{step}")
        
        return "\n".join(md)
