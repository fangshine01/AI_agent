"""Stats dashboard components — 各區塊獨立 @st.fragment auto-refresh"""

from components.stats.health_metrics import render_health_metrics
from components.stats.doc_overview import render_doc_overview
from components.stats.token_charts import render_token_charts
from components.stats.search_analytics import render_search_analytics
from components.stats.system_resources import render_system_resources

__all__ = [
    "render_health_metrics",
    "render_doc_overview",
    "render_token_charts",
    "render_search_analytics",
    "render_system_resources",
]
