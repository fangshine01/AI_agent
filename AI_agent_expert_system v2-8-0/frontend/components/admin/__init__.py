# Admin Components Package
from components.admin.doc_manager import render_document_manager
from components.admin.token_charts import render_token_charts
from components.admin.health_monitor import render_health_tab
from components.admin.config_form import render_config_tab
from components.admin.gdpr_panel import render_gdpr_panel

__all__ = [
    "render_document_manager",
    "render_token_charts",
    "render_health_tab",
    "render_config_tab",
    "render_gdpr_panel",
]
