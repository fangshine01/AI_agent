# -*- coding: utf-8 -*-
"""
語意重排序模組

使用 AI 對搜尋結果進行語意重排序,提升搜尋精準度
"""

import json
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def semantic_rerank(results: List[Dict], query: str, top_k: int = None) -> List[Dict]:
    """
    使用 AI 對搜尋結果重新排序
    
    適用於需要深度理解查詢意圖的場景
    
    Args:
        results: 搜尋結果列表
        query: 查詢字串
        top_k: 返回前 k 個結果 (None 表示全部)
        
    Returns:
        重新排序後的結果列表
    """
    if not results:
        return results
    
    # 只重排前 20 個結果 (避免 token 過多)
    candidates_to_rerank = results[:20]
    remaining_results = results[20:]
    
    try:
        # 構建重排序 prompt
        candidates = []
        for idx, result in enumerate(candidates_to_rerank):
            candidates.append({
                'index': idx,
                'title': result.get('source_title', result.get('file_name', '')),
                'content': result.get('content', result.get('text_content', result.get('raw_content', '')))[:200]  # 只取前 200 字
            })
        
        prompt = f"""你是一個嚴格的搜尋結果排序專家。
用戶查詢:「{query}」

請分析每個候選結果，並根據以下規則排序：
1. 【關鍵實體匹配】(最高權重): 如果查詢包含特定的產品型號(如 N706)、機台編號或錯誤代碼，優先展示"完全匹配"的結果。
2. 【排除不相關】: 如果結果明確屬於另一個不同型號的產品(例如查 N706 卻出現 N500 的文件)，請將其排在最後面或過濾掉。
3. 【內容相關性】: 解決方案的具體程度與問題的關聯性。

候選結果 (編號 0-{len(candidates)-1}):
{json.dumps(candidates, ensure_ascii=False, indent=2)}

請根據與查詢的相關性,將結果編號由高到低排序。
只回覆 JSON 陣列,例如: [3, 0, 7, 1, ...]
"""
        
        
        from core import ai_core
        # 使用 analyze_slide (text_only 模式) 來替代不存在的 analyze_text
        response, _ = ai_core.analyze_slide(prompt, api_mode="text_only", text_model="gpt-4o-mini")
        
        # 清理可能的 Markdown 標記
        if response.startswith("```"):
             lines = response.split('\n')
             if lines[0].startswith("```"):
                 response = "\n".join(lines[1:-1])
        
        # 解析 AI 回應
        reranked_indices = json.loads(response)
        
        # 重新排列
        reranked_results = []
        for i in reranked_indices:
            if isinstance(i, int) and 0 <= i < len(candidates_to_rerank):
                reranked_results.append(candidates_to_rerank[i])
        
        # 加上未重排的其餘結果
        final_results = reranked_results + remaining_results
        
        logger.info(f"✓ 語意重排序完成: {len(reranked_results)} 個結果")
        
        if top_k:
            return final_results[:top_k]
        return final_results
        
    except Exception as e:
        logger.warning(f"重排序失敗: {e}")
        return results


def expand_query(query: str, max_variants: int = 3) -> List[str]:
    """
    查詢擴展:生成語意相近的查詢變體
    
    例如: "如何安裝" → ["如何安裝", "安裝步驟", "安裝流程", "安裝教學"]
    
    Args:
        query: 原始查詢
        max_variants: 最多生成幾個變體
        
    Returns:
        擴展後的查詢列表 (包含原始查詢)
    """
    try:
        from core import ai_core
        
        prompt = f"""請為以下查詢生成 {max_variants} 個語意相近的變體查詢,幫助提升搜尋召回率:

原始查詢:「{query}」

要求:
1. 保留核心意圖
2. 使用同義詞或不同表達方式
3. 只回覆 JSON 陣列,例如: ["變體1", "變體2", "變體3"]
"""
        
        response = ai_core.analyze_text(prompt, model="gpt-4o-mini")
        variants = json.loads(response)
        
        # 包含原始查詢
        return [query] + variants[:max_variants]
        
    except Exception as e:
        logger.warning(f"查詢擴展失敗: {e}")
        return [query]


def reciprocal_rank_fusion(
    vector_results: List[Dict],
    keyword_results: List[Dict],
    k: int = 60
) -> List[Dict]:
    """
    RRF (Reciprocal Rank Fusion) 融合演算法
    
    score(d) = sum(1 / (k + rank_i))
    
    Args:
        vector_results: 向量搜尋結果
        keyword_results: 關鍵字搜尋結果
        k: RRF 參數 (預設 60)
        
    Returns:
        融合後的結果列表
    """
    scores = {}
    
    # Vector results
    for rank, result in enumerate(vector_results, 1):
        chunk_id = result.get('chunk_id', result.get('id'))
        if chunk_id:
            scores[chunk_id] = scores.get(chunk_id, 0) + 1 / (k + rank)
            # 保存結果物件
            if chunk_id not in scores or 'result' not in scores.get(chunk_id, {}):
                scores[chunk_id] = {'score': scores.get(chunk_id, 0), 'result': result}
    
    # Keyword results
    for rank, result in enumerate(keyword_results, 1):
        chunk_id = result.get('chunk_id', result.get('id'))
        if chunk_id:
            current_score = scores.get(chunk_id, {}).get('score', 0)
            scores[chunk_id] = {
                'score': current_score + 1 / (k + rank),
                'result': result
            }
    
    # 排序
    sorted_items = sorted(scores.items(), key=lambda x: x[1]['score'], reverse=True)
    
    # 提取結果並添加融合分數
    fused_results = []
    for chunk_id, data in sorted_items:
        result = data['result'].copy()
        result['fusion_score'] = data['score']
        fused_results.append(result)
    
    return fused_results


if __name__ == "__main__":
    # 測試語意重排序
    logging.basicConfig(level=logging.INFO)
    
    # 模擬搜尋結果
    test_results = [
        {'index': 0, 'title': 'N706 蝴蝶Mura', 'content': '蝴蝶狀的 Mura 缺陷分析...'},
        {'index': 1, 'title': 'ITO issue', 'content': 'ITO 製程問題...'},
        {'index': 2, 'title': 'Oven Pin', 'content': 'Oven Pin 異常處理...'},
    ]
    
    print("測試語意重排序:")
    reranked = semantic_rerank(test_results, "N706 蝴蝶 問題")
    for i, result in enumerate(reranked, 1):
        print(f"{i}. {result['title']}")
    
    print("\n測試查詢擴展:")
    expanded = expand_query("如何解決問題")
    print(f"原始查詢: '如何解決問題'")
    print(f"擴展結果: {expanded}")
