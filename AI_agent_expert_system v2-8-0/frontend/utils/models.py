"""
模型清單 — 唯一定義

依據 GPT_support.md，含 OpenAI / Google / Azure 共 31 個模型 (v2.4.0)
Chat 和 Admin 頁面共同引用此清單，消除重複定義
"""

from typing import List, Dict

AVAILABLE_MODELS: List[Dict[str, str]] = [
    # ===== OpenAI 平台 =====
    {"display_name": "OpenAI-GPT-4o",          "model_id": "gpt-4o",               "category": "OpenAI 標準", "cost_label": "💰💰"},
    {"display_name": "OpenAI-GPT-4o-mini",     "model_id": "gpt-4o-mini",          "category": "OpenAI 標準", "cost_label": "💰"},
    {"display_name": "OpenAI-GPT-4.1",         "model_id": "gpt-4.1",              "category": "OpenAI 進階", "cost_label": "💰💰💰"},
    {"display_name": "OpenAI-GPT-4.1-Mini",    "model_id": "gpt-4.1-mini",         "category": "OpenAI 輕量", "cost_label": "💰"},
    {"display_name": "OpenAI-GPT-4-Turbo",     "model_id": "gpt-4-turbo-preview",  "category": "OpenAI 舊版", "cost_label": "💰💰💰"},
    {"display_name": "OpenAI-GPT-4-Vision",    "model_id": "gpt-4-vision-preview", "category": "OpenAI 視覺", "cost_label": "💰💰💰"},
    {"display_name": "OpenAI-O1",              "model_id": "o1",                   "category": "OpenAI 推理", "cost_label": "💰💰💰"},
    {"display_name": "OpenAI-O1-Mini",         "model_id": "o1-mini",              "category": "OpenAI 推理", "cost_label": "💰💰"},
    {"display_name": "OpenAI-O3-mini",         "model_id": "o3-mini",              "category": "OpenAI 推理", "cost_label": "💰💰"},
    {"display_name": "OpenAI-O4-Mini",         "model_id": "o4-mini",              "category": "OpenAI 推理", "cost_label": "💰💰"},
    {"display_name": "GPT-5-mini",             "model_id": "gpt-5-mini",           "category": "OpenAI 未來", "cost_label": "💰💰"},
    {"display_name": "GPT-5.1",                "model_id": "gpt-5.1",              "category": "OpenAI 未來", "cost_label": "💰💰💰"},
    # ===== Google 平台 =====
    {"display_name": "Google-Gemini-2.5-Pro",       "model_id": "gemini-2.5-pro",             "category": "Google 進階", "cost_label": "💰💰💰"},
    {"display_name": "Google-Gemini-2.5-Flash",      "model_id": "gemini-2.5-flash",           "category": "Google 標準", "cost_label": "💰"},
    {"display_name": "Google-Gemini-2.5-Flash-Lite", "model_id": "gemini-2.5-flash-lite",      "category": "Google 輕量", "cost_label": "💰"},
    {"display_name": "Google-Gemini-2.0-Flash",      "model_id": "gemini-2.0-flash",           "category": "Google 標準", "cost_label": "💰"},
    {"display_name": "Google-Gemini-2.0-Flash-Lite", "model_id": "gemini-2.0-flash-lite",      "category": "Google 輕量", "cost_label": "💰"},
    {"display_name": "Google-Gemini-1.5-Flash",      "model_id": "gemini-1.5-flash-latest",    "category": "Google 舊版", "cost_label": "💰"},
    {"display_name": "Gemini-3-Pro-Preview",         "model_id": "gemini-3-pro-preview",       "category": "Google 未來", "cost_label": "💰💰💰"},
    {"display_name": "Gemini-3-Flash-Preview",       "model_id": "gemini-3-flash-preview",     "category": "Google 未來", "cost_label": "💰💰"},
    {"display_name": "Gemini-2.5-Flash-Image",       "model_id": "gemini-2.5-flash-image",     "category": "Google 視覺", "cost_label": "💰💰"},
    {"display_name": "Gemini-3-Pro-Image",           "model_id": "gemini-3-pro-image-preview", "category": "Google 視覺", "cost_label": "💰💰💰"},
    # ===== Azure 平台 =====
    {"display_name": "Azure-GPT-4o",        "model_id": "gpt-4o",      "category": "Azure 標準", "cost_label": "💰💰"},
    {"display_name": "Azure-GPT-4o-mini",   "model_id": "gpt-4o-mini", "category": "Azure 標準", "cost_label": "💰"},
    {"display_name": "Azure-GPT-4o-0806",   "model_id": "gpt-4o-0806", "category": "Azure 標準", "cost_label": "💰💰"},
    {"display_name": "Azure-GPT-4.1",       "model_id": "gpt-4.1",     "category": "Azure 進階", "cost_label": "💰💰💰"},
    {"display_name": "Azure-GPT-4.1-Mini",  "model_id": "gpt-4.1-mini","category": "Azure 輕量", "cost_label": "💰"},
    {"display_name": "Azure-O1-Mini",       "model_id": "o1-mini",     "category": "Azure 推理", "cost_label": "💰💰"},
    {"display_name": "Azure-GPT-O4-Mini",   "model_id": "o4-mini",     "category": "Azure 推理", "cost_label": "💰💰"},
    {"display_name": "Azure-GPT-4-Turbo",   "model_id": "gpt-4",       "category": "Azure 舊版", "cost_label": "💰💰💰"},
    {"display_name": "Azure-GPT-5.1",       "model_id": "gpt-5.1",     "category": "Azure 未來", "cost_label": "💰💰💰"},
]


def format_model_display(m) -> str:
    """將模型物件格式化為下拉選單顯示文字（Chat + Admin 共用）"""
    if isinstance(m, dict):
        cost = m.get("cost_label", "")
        cat = m.get("category", "")
        name = m.get("display_name", m.get("model_id", ""))
        return f"{cost} {name}  ({cat})" if cat else f"{cost} {name}"
    return str(m)


def get_model_id(model_obj) -> str:
    """從模型物件取得 model_id"""
    if isinstance(model_obj, dict):
        return model_obj.get("model_id", "gpt-4o-mini")
    return str(model_obj)
