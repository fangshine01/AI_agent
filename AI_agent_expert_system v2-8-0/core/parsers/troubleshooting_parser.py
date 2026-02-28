"""
異常報告解析器
將 Troubleshooting 文件標準化為完整 8D 報告 (v5.0 - 單一 Chunk 策略)
"""

from typing import List, Dict
import logging
import re
from .base_parser import BaseParser

logger = logging.getLogger(__name__)


class TroubleshootingParser(BaseParser):
    """異常報告解析器 - 合併為單一完整 8D 報告 Chunk"""
    
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
        將異常報告解析為單一整合 Chunk (含完整 8D 結構)
        
        Args:
            raw_data: 原始文件內容 (字串)
        
        Returns:
            List[Dict]: 包含單一 chunk 的列表
                [{
                    'type': 'troubleshooting_full',
                    'title': '8D 報告標題',
                    'content': '完整 Markdown 內容',
                    'metadata': { 'fields': {...}, 'yield_loss': '...', ... }
                }]
        """
        logger.info("開始解析 Troubleshooting 文件 (v5.0 - 合併模式)...")
        
        # 構建 AI 分析 Prompt
        prompt = f"""你是一位專業的品質工程師。請分析以下異常報告,並將內容歸納為以下 6 個標準欄位。
若原始資料中缺少某些欄位,請根據上下文合理推斷。

同時請額外提取以下資訊(若有):
- product: 產品型號 (如 N706, N707 等)
- defect_code: 缺陷代碼/異常名稱 (如 Oven Pin, 蝴蝶Mura 等)
- station: 檢出站點 (如 PTST, A3LR, LCD2 等)
- yield_loss: 產量損失百分比 (如 8%, 7.2% 等)

請以以下 JSON 格式回傳:
{{
    "Problem issue & loss": "...",
    "Problem description": "...",
    "Analysis root cause": "...",
    "Containment action": "...",
    "Corrective action": "...",
    "Preventive action": "...",
    "product": "產品型號或null",
    "defect_code": "缺陷代碼或null",
    "station": "站點或null",
    "yield_loss": "損失百分比或null"
}}

原始內容:
{raw_data}
"""
        
        try:
            # 呼叫 AI 分析
            response = self.ai_core.analyze_slide(prompt, api_mode="text_only")
            
            # 提取 JSON
            extracted = self.extract_json_from_response(response)
            
            # 生成整合的 Markdown 內容
            md_content = self._generate_8d_markdown(extracted)
            
            # 提取 metadata
            metadata = {
                'fields': {field: extracted.get(field, '未提供') for field in self.STANDARD_FIELDS},
                'product': extracted.get('product'),
                'defect_code': extracted.get('defect_code'),
                'station': extracted.get('station'),
                'yield_loss': extracted.get('yield_loss')
            }
            
            # 決定標題
            title = extracted.get('Problem issue & loss', '異常報告')
            if metadata.get('product') and metadata.get('defect_code'):
                title = f"{metadata['product']} - {metadata['defect_code']}"
            
            # 回傳單一 chunk
            chunk = {
                'type': 'troubleshooting_full',
                'title': title,
                'content': md_content,
                'metadata': metadata
            }
            
            # 驗證切片
            validated_chunks = self.validate_chunks([chunk])
            
            logger.info(f"✅ Troubleshooting 解析完成 (合併為 1 個 chunk)")
            return validated_chunks
            
        except Exception as e:
            logger.error(f"❌ Troubleshooting 解析失敗: {e}")
            # 回傳基本結構
            return [
                {
                    'type': 'troubleshooting_full',
                    'title': '原始內容',
                    'content': raw_data[:2000] + "..." if len(raw_data) > 2000 else raw_data,
                    'metadata': {}
                }
            ]
    
    def _generate_8d_markdown(self, data: Dict) -> str:
        """
        生成 8D 格式的 Markdown 文件
        
        Args:
            data: AI 提取的結構化資料
        
        Returns:
            str: 完整的 Markdown 格式 8D 報告
        """
        md = []
        
        # 標題
        title = data.get('Problem issue & loss', '異常報告')
        product = data.get('product', '')
        defect = data.get('defect_code', '')
        
        if product and defect:
            md.append(f"# 【8D 異常報告】{product} - {defect}\n")
        else:
            md.append(f"# 【8D 異常報告】{title}\n")
        
        # 基本資訊
        md.append("## 基本資訊\n")
        if data.get('product'):
            md.append(f"- **產品型號**: {data['product']}")
        if data.get('defect_code'):
            md.append(f"- **缺陷代碼**: {data['defect_code']}")
        if data.get('station'):
            md.append(f"- **檢出站點**: {data['station']}")
        if data.get('yield_loss'):
            md.append(f"- **Yield Loss**: {data['yield_loss']}")
        md.append("")
        
        # 8D 欄位 - 格式化處理
        for field in self.STANDARD_FIELDS:
            content = data.get(field, '未提供')
            if content and content != '未提供':
                md.append(f"## {field}\n")
                
                # 格式化內容
                formatted_content = self._format_content(content)
                md.append(f"{formatted_content}\n")
        
        return "\n".join(md)
    
    def _format_content(self, content: str) -> str:
        """
        格式化內容,確保有適當的段落分隔和條列格式
        
        Args:
            content: 原始內容
        
        Returns:
            str: 格式化後的內容
        """
        if content is None:
            return '未提供'
            
        # 處理 list 類型的輸入 (AI 可能回傳 JSON Array)
        if isinstance(content, list):
            formatted = []
            for item in content:
                if item:
                    formatted.append(f"- {str(item).strip()}")
            return '\n'.join(formatted) if formatted else '未提供'
            
        if not isinstance(content, str) or content.strip() == '':
            return '未提供'
        
        # 移除多餘的空白和換行
        content = content.strip()
        
        # 如果內容已經有 Markdown 格式 (包含 #, -, *, 等),直接返回
        if any(marker in content for marker in ['- ', '* ', '1. ', '2. ', '## ', '### ']):
            return content
        
        # 如果內容包含句號或分號,嘗試分段
        if '。' in content or ';' in content or '；' in content:
            # 按句號或分號分段
            sentences = re.split(r'[。；;]', content)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            # 如果分段後有多個句子,使用條列式
            if len(sentences) > 1:
                formatted = []
                for i, sentence in enumerate(sentences, 1):
                    if sentence:
                        # 如果句子很短 (< 20 字),可能是標題或關鍵字
                        if len(sentence) < 20:
                            formatted.append(f"- **{sentence}**")
                        else:
                            formatted.append(f"{i}. {sentence}")
                return '\n'.join(formatted)
        
        # 如果內容包含換行,保留換行
        if '\n' in content:
            lines = content.split('\n')
            lines = [line.strip() for line in lines if line.strip()]
            
            # 如果有多行,使用條列式
            if len(lines) > 1:
                formatted = []
                for line in lines:
                    if line:
                        formatted.append(f"- {line}")
                return '\n'.join(formatted)
        
        # 如果內容很長 (> 100 字),嘗試按逗號分段
        if len(content) > 100 and (',' in content or '、' in content):
            parts = re.split(r'[,、]', content)
            parts = [p.strip() for p in parts if p.strip()]
            
            if len(parts) > 2:
                formatted = []
                for part in parts:
                    if part:
                        formatted.append(f"- {part}")
                return '\n'.join(formatted)
        
        # 預設:直接返回內容
        return content



if __name__ == "__main__":
    print("TroubleshootingParser v5.0 定義完成 (單一 Chunk 策略)")
