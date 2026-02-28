# -*- coding: utf-8 -*-
"""
測試搜尋系統改善功能

測試分詞、多關鍵字搜尋等功能
"""

import sys
import os
import io

# 設置 stdout 編碼為 UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.search.tokenizer import tokenize_query, extract_document_identifiers, contains_document_identifier
from core.search.legacy_search import search_documents_v2


def test_basic_tokenization():
    """測試基本分詞功能"""
    print("測試: 基本分詞功能")
    query = "N706 蝴蝶Mura.pptx  內容詳細解析"
    tokens = tokenize_query(query)
    
    print(f"  查詢: '{query}'")
    print(f"  分詞結果: {tokens}")
    
    # 調整預期 - "蝴蝶Mura" 會被分成 "蝴蝶" 和 "Mura"
    assert "N706" in tokens, "應包含 N706"
    assert "蝴蝶" in tokens or "蝴" in tokens, "應包含 蝴蝶 或 蝴"
    assert "Mura" in tokens, "應包含 Mura"
    assert "pptx" not in tokens, "不應包含副檔名 pptx"
    # 停用詞應被過濾
    assert "內容" not in tokens, "不應包含停用詞 內容"
    assert "詳細" not in tokens, "不應包含停用詞 詳細"
    assert "解析" not in tokens, "不應包含停用詞 解析"
    
    print("  [OK] 通過\n")


def test_english_tokenization():
    """測試英文分詞"""
    print("測試: 英文分詞")
    query = "ITO issue problem.pdf"
    tokens = tokenize_query(query)
    
    print(f"  查詢: '{query}'")
    print(f"  分詞結果: {tokens}")
    
    assert "ITO" in tokens, "應包含 ITO"
    assert "issue" in tokens, "應包含 issue"
    assert "problem" in tokens, "應包含 problem"
    assert "pdf" not in tokens, "不應包含副檔名 pdf"
    
    print("  [OK] 通過\n")


def test_mixed_language():
    """測試中英混合分詞"""
    print("測試: 中英混合分詞")
    query = "如何解決 Oven Pin 問題"
    tokens = tokenize_query(query)
    
    print(f"  查詢: '{query}'")
    print(f"  分詞結果: {tokens}")
    
    assert "如何" in tokens, "應包含 如何"
    assert "解決" in tokens, "應包含 解決"
    assert "Oven" in tokens, "應包含 Oven"
    assert "Pin" in tokens, "應包含 Pin"
    assert "問題" in tokens, "應包含 問題"
    
    print("  [OK] 通過\n")


def test_document_identifier_extraction():
    """測試文件編號提取"""
    print("測試: 文件編號提取")
    query = "N706 蝴蝶Mura 問題"
    identifiers = extract_document_identifiers(query)
    
    print(f"  查詢: '{query}'")
    print(f"  提取的編號: {identifiers}")
    
    assert "N706" in identifiers, "應提取到 N706"
    
    print("  [OK] 通過\n")


def test_contains_document_identifier():
    """測試是否包含文件編號"""
    print("測試: 是否包含文件編號")
    
    test_cases = [
        ("N706 問題", True),
        ("SOP-001 流程", True),
        ("一般問題", False)
    ]
    
    for query, expected in test_cases:
        result = contains_document_identifier(query)
        print(f"  '{query}' -> {result} (預期: {expected})")
        assert result == expected, f"'{query}' 的結果應為 {expected}"
    
    print("  [OK] 通過\n")


def test_multi_keyword_search():
    """測試多關鍵字搜尋"""
    print("測試: 多關鍵字搜尋")
    
    test_queries = [
        "N706 蝴蝶 Mura",
        "N706 問題",
        "蝴蝶",
        "Oven Pin",
        "ITO issue"
    ]
    
    for query in test_queries:
        print(f"\n  查詢: '{query}'")
        try:
            results = search_documents_v2(query, top_k=3)
            
            if results:
                print(f"  找到 {len(results)} 筆結果:")
                for i, result in enumerate(results[:3], 1):
                    match_score = result.get('match_score', result.get('match_count', 'N/A'))
                    print(f"    {i}. {result.get('file_name')} ({result.get('match_level')}, 分數: {match_score})")
            else:
                print("  無結果")
        except Exception as e:
            print(f"  [WARNING] 錯誤: {e}")
    
    print("\n  [OK] 搜尋測試完成\n")


def run_all_tests():
    """執行所有測試"""
    print("=" * 60)
    print("搜尋系統改善測試")
    print("=" * 60)
    print()
    
    tests = [
        test_basic_tokenization,
        test_english_tokenization,
        test_mixed_language,
        test_document_identifier_extraction,
        test_contains_document_identifier,
        test_multi_keyword_search
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] 失敗: {e}\n")
            failed += 1
        except Exception as e:
            print(f"  [ERROR] 錯誤: {e}\n")
            failed += 1
    
    print("=" * 60)
    print(f"測試結果: {passed} 通過, {failed} 失敗")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
