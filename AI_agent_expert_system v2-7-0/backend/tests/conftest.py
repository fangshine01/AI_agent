"""
測試共用設定 (conftest.py)

提供 pytest fixture 給所有測試模組使用
"""

import sys
from pathlib import Path

# 確保專案根目錄在 sys.path 中
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
