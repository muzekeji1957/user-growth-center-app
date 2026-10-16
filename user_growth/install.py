# -*- coding: utf-8 -*-
"""App 安装 / 迁移入口（由 hooks.after_install / after_migrate 调用）。

职责：
    1. 创建自定义角色「增长分析师 Growth Analyst」。
    2. 创建「用户增长中心」Workspace，把三个交付物挂到工作台。
    3. 写入 Growth Product 主数据（复用内容工厂真实在售产品）。
    4. 可选：写入 mock 演示数据（环境变量 USER_GROWTH_SEED=1 时开启）。
"""

import frappe

from user_growth.seed.products import PRODUCTS


def after_install():
    _create_role()
    _create_workspace()
    _seed_products()
    if frappe.conf.get("USER_GROWTH_SEED") or False:
        from user_growth.seed.mock_data import seed

        seed(n_customers=420)


def after_migrate():
    # 迁移时确保主数据存在（不重复）
    _seed_products(silent=True)


# ----------------------------------------------------------------------
def _create_role():
    if frappe.db.exists("Role", "Growth Analyst"):
        return
    frappe.get_doc(
        {
            "doctype": "Role",
            "role_name": "Growth Analyst",
            "desk_access": 1,
            "description": "用户增长中心的分析与查看角色",
        }
    ).insert(ignore_permissions=True)


def _create_workspace():
    if frappe.db.exists("Workspace", "用户增长中心"):
        return
    ws = frappe.get_doc(
        {
            "doctype": "Workspace",
            "workspace_name": "用户增长中心",
            "label": "用户增长中心",
            "module": "User Growth",
            "icon": "octicon octicon-graph",
            "color": "#16B1A7",
            "content": [
                {
                    "type": "header",
                    "data": {"text": "用户增长中心", "style": "Heading 1"},
                },
                {
                    "type": "card",
                    "data": {
                        "label": "用户服务单据",
                        "links": [
                            {"label": "新建服务单据", "type": "DocType", "name": "User Service Record"},
                            {"label": "产品目录", "type": "DocType", "name": "Growth Product"},
                        ],
                    },
                },
                {
                    "type": "card",
                    "data": {
                        "label": "分析看板",
                        "links": [
                            {"label": "用户增长分析报表", "type": "Report", "name": "User Growth Report"},
                            {"label": "用户增长数据大屏", "type": "Page", "name": "user-growth-dashboard"},
                        ],
                    },
                },
            ],
        }
    )
    ws.insert(ignore_permissions=True)


def _seed_products(silent=False):
    created = 0
    for p in PRODUCTS:
        if frappe.db.exists("Growth Product", p["product_code"]):
            continue
        frappe.get_doc(
            {
                "doctype": "Growth Product",
                "product_code": p["product_code"],
                "product_name": p["product_name"],
                "category": p["category"],
                "price": p["price"],
                "service_days": p["service_days"],
                "billing_cycle": p["billing_cycle"],
                "platform": p["platform"],
                "audience": p["audience"],
                "selling_point": p["selling_point"],
                "description": p["description"],
            }
        ).insert(ignore_permissions=True)
        created += 1
    if created and not silent:
        frappe.msgprint("已写入 %d 个产品主数据" % created)
