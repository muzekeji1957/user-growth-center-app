# -*- coding: utf-8 -*-
"""用户增长分析报表（Script Report）。

提供四种分析视图，全部复用 analytics 口径：
    * 月度趋势：期初/新增/续费/升级/流失/净增/期末/流失率/环比 + 折线图 + 摘要卡。
    * 渠道维度 / 产品线维度 / 区域维度：客户数、收入、流失率排行。
"""

import frappe

from user_growth.analytics import (
    build_dashboard_payload,
    dimension_breakdown,
    monthly_trend,
)


def execute(filters=None):
    filters = filters or {}
    view = filters.get("view") or "月度趋势"
    months = int(filters.get("months") or 13)

    rows = frappe.db.get_all(
        "User Service Record",
        filters={"docstatus": 1},
        fields=[
            "customer_name", "customer_code", "customer_type", "region", "channel",
            "product_line", "product", "service_type", "status", "amount",
            "service_start", "churn_date", "churn_reason", "is_winback",
            "activity_score", "lifetime_days", "is_key_account", "nps_type",
        ],
    )
    records = [dict(r) for r in rows]

    if view == "月度趋势":
        return _monthly(records, months)
    return _dimension(records, view)


def _monthly(records, months):
    trend = monthly_trend(records, months=months)
    columns = [
        {"fieldname": "period", "label": "月份", "fieldtype": "Data", "width": 90},
        {"fieldname": "opening", "label": "期初存量", "fieldtype": "Int", "width": 90},
        {"fieldname": "new", "label": "新增", "fieldtype": "Int", "width": 70},
        {"fieldname": "renew", "label": "续费", "fieldtype": "Int", "width": 70},
        {"fieldname": "upgrade", "label": "升级", "fieldtype": "Int", "width": 70},
        {"fieldname": "churn", "label": "流失", "fieldtype": "Int", "width": 70},
        {"fieldname": "net", "label": "净增", "fieldtype": "Int", "width": 70},
        {"fieldname": "closing", "label": "期末存量", "fieldtype": "Int", "width": 90},
        {"fieldname": "revenue", "label": "营收(元)", "fieldtype": "Currency", "width": 110},
        {"fieldname": "churn_rate", "label": "流失率", "fieldtype": "Percent", "width": 80},
        {"fieldname": "net_growth_rate", "label": "净增长率", "fieldtype": "Percent", "width": 80},
        {"fieldname": "new_mom", "label": "新增环比", "fieldtype": "Percent", "width": 80},
    ]
    data = []
    for t in trend:
        row = dict(t)
        row["churn_rate"] = (t["churn_rate"] or 0) / 100.0
        row["net_growth_rate"] = (t["net_growth_rate"] or 0) / 100.0
        row["new_mom"] = (t["new_mom"] / 100.0) if t.get("new_mom") is not None else None
        data.append(row)

    chart = {
        "type": "line",
        "title": "月度增长与流失趋势",
        "data": {
            "labels": [t["period"] for t in trend],
            "datasets": [
                {"name": "期末存量", "values": [t["closing"] for t in trend]},
                {"name": "新增", "values": [t["new"] for t in trend]},
                {"name": "流失", "values": [t["churn"] for t in trend]},
                {"name": "营收(元)", "values": [t["revenue"] for t in trend]},
            ],
        },
        "height": 320,
    }

    last = trend[-1] if trend else {}
    prev = trend[-2] if len(trend) > 1 else {}
    report_summary = [
        {"label": "期末在服客户", "value": last.get("closing", 0), "indicator": "Blue", "datatype": "Int"},
        {"label": "本月新增", "value": last.get("new", 0), "indicator": "Green", "datatype": "Int"},
        {"label": "本月流失", "value": last.get("churn", 0), "indicator": "Red", "datatype": "Int"},
        {"label": "本月营收(元)", "value": last.get("revenue", 0), "indicator": "Green", "datatype": "Currency"},
        {"label": "本月流失率", "value": (last.get("churn_rate") or 0) / 100.0, "indicator": "Orange", "datatype": "Percent"},
    ]
    return columns, data, None, chart, report_summary


def _dimension(records, view):
    field = {"渠道维度": "channel", "产品线维度": "product_line", "区域维度": "region"}.get(view, "channel")
    rows = dimension_breakdown(records, field)
    columns = [
        {"fieldname": "name", "label": field.replace("product_line", "产品线").replace("channel", "渠道").replace("region", "区域"), "fieldtype": "Data", "width": 140},
        {"fieldname": "customers", "label": "客户数", "fieldtype": "Int", "width": 80},
        {"fieldname": "customer_share", "label": "客户占比", "fieldtype": "Percent", "width": 90},
        {"fieldname": "orders", "label": "有效订单", "fieldtype": "Int", "width": 90},
        {"fieldname": "revenue", "label": "收入(元)", "fieldtype": "Currency", "width": 110},
        {"fieldname": "revenue_share", "label": "收入占比", "fieldtype": "Percent", "width": 90},
        {"fieldname": "avg_amount", "label": "客单价", "fieldtype": "Currency", "width": 100},
        {"fieldname": "churned", "label": "流失数", "fieldtype": "Int", "width": 80},
        {"fieldname": "churn_rate", "label": "流失率", "fieldtype": "Percent", "width": 80},
        {"fieldname": "net", "label": "净留存", "fieldtype": "Int", "width": 80},
    ]
    data = []
    for r in rows:
        row = dict(r)
        row["customer_share"] = r["customer_share"] / 100.0
        row["revenue_share"] = r["revenue_share"] / 100.0
        row["churn_rate"] = r["churn_rate"] / 100.0
        data.append(row)

    chart = {
        "type": "bar",
        "title": "%s：客户数 vs 流失率" % view,
        "data": {
            "labels": [r["name"] for r in rows],
            "datasets": [
                {"name": "客户数", "values": [r["customers"] for r in rows]},
                {"name": "流失率(%)", "values": [r["churn_rate"] * 100 for r in rows]},
            ],
        },
        "height": 320,
    }
    report_summary = [
        {"label": "%s数" % ("渠道" if field == "channel" else ("产品线" if field == "product_line" else "区域")), "value": len(rows), "indicator": "Blue", "datatype": "Int"},
        {"label": "总客户数", "value": sum(r["customers"] for r in rows), "indicator": "Green", "datatype": "Int"},
        {"label": "总收入(元)", "value": sum(r["revenue"] for r in rows), "indicator": "Green", "datatype": "Currency"},
        {"label": "平均流失率", "value": (sum(r["churn_rate"] for r in rows) / len(rows) / 100.0) if rows else 0, "indicator": "Orange", "datatype": "Percent"},
    ]
    return columns, data, None, chart, report_summary
