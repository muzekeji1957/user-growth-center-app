# -*- coding: utf-8 -*-
"""定时任务：刷新大屏快照缓存，保证大屏准实时且高峰不卡。

由 hooks.scheduler_events 每 10 分钟调用一次；daily 也跑一遍兜底。
"""

import frappe

from user_growth.api import get_growth_dashboard

DASHBOARD_CACHE_KEY = "user_growth:dashboard_snapshot"


def refresh_growth_snapshot():
    try:
        get_growth_dashboard(months=13, refresh=1)
        frappe.logger().info("user_growth: dashboard snapshot refreshed")
    except Exception:
        frappe.log_error(title="user_growth: refresh_growth_snapshot failed")
