# -*- coding: utf-8 -*-
"""把 mock 演示数据写入 Frappe（bench execute 入口）。

用法：
    bench execute user_growth.seed.mock_data.seed --kwargs "{'n_customers': 420}"

默认只写入未写过的数据（再次执行不会重复灌）。会把单据直接置为"已提交"，
这样装完即可在报表/大屏看到真实可用的增长与流失曲线。
"""

import frappe

from .generator import build_records


def seed(n_customers=420, force=False):
    if not force and frappe.db.count("User Service Record") > 50:
        frappe.msgprint("已存在演示数据，跳过（如需重建请加 force=True）")
        return 0

    records = build_records(n_customers=n_customers)
    created = 0
    for r in records:
        r = dict(r)
        # 避免链接字段指向不存在的用户
        r.pop("sales_owner", None)
        r["owner"] = "Administrator"
        doc = frappe.new_doc("User Service Record")
        doc.update(r)
        doc.insert(ignore_permissions=True)
        if doc.docstatus == 0:
            doc.submit()
        created += 1
    frappe.db.commit()
    frappe.msgprint("已写入 %d 条演示服务单据" % created)
    return created
