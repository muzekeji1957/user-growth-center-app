from frappe import _


def get_data():
    """侧边栏「用户增长中心」模块入口（Workspace 的兜底定义）。

    注意：Frappe v14/v15 优先读取数据库中的 Workspace 记录
    （由 user_growth.install.after_install 创建），本文件用于 v13 兼容与降级。
    """
    return [
        {
            "module_name": "User Growth",
            "category": "Modules",
            "label": _("用户增长中心"),
            "color": "#16B1A7",
            "icon": "octicon octicon-graph",
            "type": "module",
            "description": _("用户服务开通/流失单据、增长分析与数据大屏"),
            "items": [
                {
                    "type": "doctype",
                    "name": "User Service Record",
                    "label": _("用户服务单据"),
                    "description": _("记录用户服务的开通、续费、升级与流失"),
                },
                {
                    "type": "doctype",
                    "name": "Growth Product",
                    "label": _("产品目录"),
                    "description": _("服务产品/套餐价目表"),
                },
                {
                    "type": "report",
                    "name": "User Growth Report",
                    "label": _("用户增长分析报表"),
                    "is_query_report": True,
                    "doctype": "User Service Record",
                    "description": _("月度增长趋势与渠道/产品线/区域维度分析"),
                },
                {
                    "type": "page",
                    "name": "user-growth-dashboard",
                    "label": _("用户增长数据大屏"),
                    "description": _("适用于大屏投放的增长数据可视化看板"),
                },
            ],
        }
    ]
