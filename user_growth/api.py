# -*- coding: utf-8 -*-
"""大屏 / 表单联动 / Jinja 的数据接口。

所有方法都走 ``analytics`` 这同一套口径，保证"报表看到的"与"大屏看到的"数字一致。
"""

import frappe

from user_growth.analytics import build_dashboard_payload

DASHBOARD_CACHE_KEY = "user_growth:dashboard_snapshot"
DASHBOARD_CACHE_TTL = 600  # 10 分钟


def _fetch_records():
    """取出所有已提交的服务单据，转成 analytics 需要的 dict 列表。"""
    rows = frappe.db.get_all(
        "User Service Record",
        filters={"docstatus": 1},
        fields=[
            "name", "customer_name", "customer_code", "customer_type", "mobile",
            "region", "channel", "product_line", "product", "service_type",
            "status", "amount", "service_start", "service_end", "billing_cycle",
            "churn_date", "churn_reason", "is_winback", "winback_score",
            "activity_score", "last_active_on", "lifetime_days", "is_key_account",
            "nps_type",
        ],
    )
    return [dict(r) for r in rows]


@frappe.whitelist()
def get_growth_dashboard(months=13, refresh=0):
    """大屏一次性拉取全部聚合数据（带缓存）。"""
    if not refresh:
        cached = frappe.cache().get_value(DASHBOARD_CACHE_KEY)
        if cached:
            return cached
    records = _fetch_records()
    payload = build_dashboard_payload(records, months=int(months))
    payload["generated_at"] = frappe.utils.now()
    payload["record_count"] = len(records)
    frappe.cache().set_value(DASHBOARD_CACHE_KEY, payload, expires_in_sec=DASHBOARD_CACHE_TTL)
    return payload


@frappe.whitelist()
def get_customer_profile(customer_code, exclude=None):
    """表单刷新时展示"该客户历史画像"（复购/流失/累计金额）。"""
    if not customer_code:
        return {}
    rows = frappe.db.get_all(
        "User Service Record",
        filters={"customer_code": customer_code, "docstatus": 1},
        fields=["name", "service_type", "amount", "status"],
    )
    total_records = len(rows)
    if exclude:
        rows = [r for r in rows if r.name != exclude]
    total_amount = sum(float(r.amount or 0) for r in rows)
    lost = sum(1 for r in rows if r.service_type == "流失" or r.status == "已流失")
    return {
        "total_records": total_records,
        "total_amount": total_amount,
        "lost_count": lost,
        "active": total_records - lost,
    }


@frappe.whitelist(allow_guest=True)
def get_growth_headline():
    """供 Jinja / 外部嵌入的极简头条（KPI 摘要）。"""
    payload = get_growth_dashboard(months=13)
    k = payload.get("kpi", {})
    return {
        "active_customers": k.get("active_customers"),
        "month_new": k.get("month_new"),
        "month_churn": k.get("month_churn"),
        "total_revenue": k.get("total_revenue"),
        "churn_rate": k.get("churn_rate"),
    }
