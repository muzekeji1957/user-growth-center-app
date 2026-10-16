app_name = "user_growth"
app_title = "用户增长中心"
app_publisher = "沐泽科技"
app_description = "用户服务开通/流失单据 · 用户增长分析报表 · 用户增长数据大屏"
app_email = "dev@muze.local"
app_license = "mit"
app_version = "1.0.0"

# 依赖：本 App 只依赖 Frappe 框架本身，不依赖 ERPNext
required_apps = []

# ------------------------------------------------------------------
# 静态资源
# ------------------------------------------------------------------
app_include_css = "/assets/user_growth/css/user_growth.css"

# ------------------------------------------------------------------
# 安装 / 升级
# ------------------------------------------------------------------
after_install = "user_growth.install.after_install"
after_migrate = "user_growth.install.after_migrate"

# ------------------------------------------------------------------
# 单据事件
# ------------------------------------------------------------------
doc_events = {
    "User Service Record": {
        "validate": "user_growth.doctype.user_service_record.user_service_record.validate",
        "before_submit": "user_growth.doctype.user_service_record.user_service_record.before_submit",
    }
}

# ------------------------------------------------------------------
# 权限查询
# ------------------------------------------------------------------
# permission_query_conditions = {
#     "User Service Record": "user_growth.doctype.user_service_record.user_service_record.get_permission_query_conditions",
# }

# ------------------------------------------------------------------
# 定时任务
# ------------------------------------------------------------------
scheduler_events = {
    "daily": [
        "user_growth.tasks.refresh_growth_snapshot",
    ],
    "cron": {
        # 每 10 分钟刷新一次大屏快照缓存
        "*/10 * * * *": [
            "user_growth.tasks.refresh_growth_snapshot",
        ]
    },
}

# ------------------------------------------------------------------
# 导出（可选）：需要时把产品目录随 App 一起同步
# ------------------------------------------------------------------
# fixtures = ["Growth Product"]

jinja = {
    "methods": [
        "user_growth.api.get_growth_headline",
    ]
}

# 大屏页面允许直接通过 /app/user-growth-dashboard 访问
website_route_rules = []
