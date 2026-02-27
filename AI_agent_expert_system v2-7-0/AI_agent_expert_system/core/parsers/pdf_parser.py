"""
PDF 解析器模組
使用 PyMuPDF (fitz) 解析 PDF 文件
"""

import fitz  # PyMuPDF
import logging
from typing import List, Dict, Any
from .base_parser import BaseParser

logger = logging.getLogger(__name__)


class PDFParser(BaseParser):
    """PDF 解析器"""

    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        """
        解析 PDF 文件
        
        Args:
            file_path: PDF 文件路徑
            
        Returns:
            List[Dict]: 切片列表
        """
        chunks = []
        try:
            doc = fitz.open(file_path)
            logger.info(f"開始解析 PDF: {file_path}, 共 {len(doc)} 頁")
            
            for page_num, page in enumerate(doc):
                # 提取文字
                text = page.get_text()
                text = self.clean_text(text)
                
                if not text:
                    continue
                
                # 建立切片
                chunk = {
                    'type': 'pdf_page',
                    'title': f"Page {page_num + 1}",
                    'content': text,
                    'page_num': page_num + 1,
                    'source': file_path
                }
                chunks.append(chunk)
                
            doc.close()
            logger.info(f"PDF 解析完成, 共 {len(chunks)} 個文字切片")
            
            # 使用父類別方法驗證切片
            return self.validate_chunks(chunks)
            
        except Exception as e:
            logger.error(f"PDF 解析失敗: {e}")
            return []

if __name__ == "__main__":
    print("PDFParser 定義完成")
