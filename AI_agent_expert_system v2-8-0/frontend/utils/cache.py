"""
集中快取函式 — 所有頁面共用
避免各頁面各自定義快取函式，統一管理 TTL 和 max_entries

依據 optimizing-streamlit-performance skill：
- @st.cache_data 用於資料載入
- @st.cache_resource 用於不可序列化的連線/客戶端物件
- 加上 max_entries 防止快取無限成長
"""

import streamlit as st
from client.api_client import APIClient


@st.cache_resource
def get_api_client(base_url: str) -> APIClient:
    """取得共用 API Client（不可序列化，使用 cache_resource）"""
    return APIClient(base_url=base_url)


@st.cache_data(ttl="30s", max_entries=10, show_spinner=False)
def cached_health_check(base_url: str) -> dict:
    """30 秒快取後端健康檢查"""
    return APIClient(base_url=base_url).health_check()


@st.cache_data(ttl="30s", max_entries=10, show_spinner=False)
def cached_detailed_health(base_url: str) -> dict:
    """30 秒快取詳細健康資訊"""
    return APIClient(base_url=base_url)._request("GET", "/health/detailed")


@st.cache_data(ttl="60s", max_entries=10, show_spinner=False)
def cached_get_stats(base_url: str) -> dict:
    """60 秒快取統計資料"""
    return APIClient(base_url=base_url).get_stats()


@st.cache_data(ttl="60s", max_entries=10, show_spinner=False)
def cached_token_stats(base_url: str) -> dict:
    """60 秒快取 Token 統計"""
    return APIClient(base_url=base_url).get_token_stats()


@st.cache_data(ttl="120s", max_entries=5, show_spinner=False)
def cached_list_documents(base_url: str) -> list:
    """120 秒快取文件列表，自動解包 API 回應的 data.documents 層"""
    resp = APIClient(base_url=base_url).list_documents()
    # list_documents() 回傳 {"success": True, "data": {"documents": [...]}}
    if isinstance(resp, dict):
        data = resp.get("data", resp)
        if isinstance(data, dict):
            return data.get("documents", [])
        if isinstance(data, list):
            return data
    if isinstance(resp, list):
        return resp
    return []
