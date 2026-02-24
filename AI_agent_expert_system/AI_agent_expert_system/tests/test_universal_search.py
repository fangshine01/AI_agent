# -*- coding: utf-8 -*-
"""
測試通用查詢引擎

驗證查詢意圖分析、策略選擇和搜尋功能
"""

import sys
import os
import io

# 設置 stdout 編碼為 UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.search import (
    universal_search,
    analyze_query_intent,
    select_search_strategy,
    QueryIntent,
    SearchStrategy
)


def test_query_intent_analysis():
    """測試查詢意圖分析"""
    print("=" * 60)
    print("測試: 查詢意圖分析")
    print("=" * 60)
    
    test_cases = [
        ("N706 蝴蝶Mura 問題", QueryIntent.TROUBLESHOOTING),
        ("如何解決 ITO issue", QueryIntent.PROCEDURAL),
        ("為什麼會出現異常", QueryIntent.TROUBLESHOOTING),
        ("找到 SOP-001 文件", QueryIntent.DOCUMENT_LOOKUP),
        ("比較 A 和 B 的差異", QueryIntent.COMPARATIVE),
        ("什麼是 Mura", QueryIntent.FACTUAL),
    ]
    
    passed = 0
    for query, expected_intent in test_cases:
        intent = analyze_query_intent(query)
        status = "[OK]" if intent == expected_intent else "[FAIL]"
        print(f"{status} '{query}' -> {intent.value} (預期: {expected_intent.value})")
        if intent == expected_intent:
            passed += 1
    
    print(f"\n結果: {passed}/{len(test_cases)} 通過\n")


def test_strategy_selection():
    """測試策略選擇"""
    print("=" * 60)
    print("測試: 搜尋策略選擇")
    print("=" * 60)
    
    test_queries = [
        "N706 蝴蝶Mura 問題",
        "如何解決 ITO issue",
        "找到 SOP-001 文件",
        "比較 Feather 和 Parquet",
    ]
    
    for query in test_queries:
        intent = analyze_query_intent(query)
        strategy = select_search_strategy(query, intent)
        print(f"查詢: '{query}'")
        print(f"  意圖: {intent.value}")
        print(f"  策略: {strategy.value}\n")


def test_universal_search():
    """測試通用搜尋引擎"""
    print("=" * 60)
    print("測試: 通用搜尋引擎")
    print("=" * 60)
    
    test_queries = [
        "N706 蝴蝶 Mura",
        "ITO issue",
        "Oven Pin",
    ]
    
    for query in test_queries:
        print(f"\n查詢: '{query}'")
        try:
            result = universal_search(query, top_k=3)
            
            print(f"  意圖: {result['intent']}")
            print(f"  策略: {result['strategy']}")
            print(f"  搜尋時間: {result['meta']['search_time']:.3f}秒")
            print(f"  信心度: {result['meta']['confidence']:.2%}")
            print(f"  找到: {result['meta']['total_found']} 筆結果")
            
            if result['results']:
                print(f"  前 3 筆結果:")
                for i, r in enumerate(result['results'][:3], 1):
                    file_name = r.get('file_name', 'N/A')
                    match_level = r.get('match_level', 'N/A')
                    score = r.get('total_score', r.get('similarity', r.get('match_score', 'N/A')))
                    print(f"    {i}. {file_name} ({match_level}, 分數: {score})")
            else:
                print("  無結果")
                
        except Exception as e:
            print(f"  [ERROR] {e}")


def run_all_tests():
    """執行所有測試"""
    print("\n")
    print("*" * 60)
    print("通用查詢引擎測試")
    print("*" * 60)
    print("\n")
    
    test_query_intent_analysis()
    test_strategy_selection()
    test_universal_search()
    
    print("\n")
    print("*" * 60)
    print("測試完成")
    print("*" * 60)


if __name__ == "__main__":
    run_all_tests()
