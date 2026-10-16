# -*- coding: utf-8 -*-
"""把预览模板构建成完全自包含的离线 HTML。

产物（双击即可打开，无需本地服务器 / 无需联网）：
    * dashboard_offline.html  用户增长数据大屏（内联 ECharts + 样式 + 渲染逻辑 + 数据）
    * report_offline.html     用户增长分析报表（内联 ECharts + Frappe 皮肤 + 数据）
    * form_offline.html       用户服务单据表单（内联 Frappe 皮肤）

用法：python build_offline.py
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "..", "user_growth")


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def build(src, dst, tokens):
    html = read(os.path.join(HERE, src))
    for k, v in tokens.items():
        html = html.replace(k, v)
    with open(os.path.join(HERE, dst), "w", encoding="utf-8") as f:
        f.write(html)
    print("built %-24s %.1f KB" % (dst, len(html) / 1024))


def main():
    echarts = read(os.path.join(HERE, "echarts.min.js"))
    data = read(os.path.join(HERE, "mock_data.json")).strip()
    css = read(os.path.join(PKG, "public", "css", "user_growth.css"))
    js = read(os.path.join(PKG, "page", "user_growth_dashboard", "user_growth_dashboard.js"))
    skin = read(os.path.join(HERE, "frappe-skin.css"))

    build(
        "dashboard.html", "dashboard_offline.html",
        {"/*__UG_CSS__*/": css, "/*__ECHARTS__*/": echarts,
         "/*__UG_DATA__*/null": data, "/*__UG_JS__*/": js},
    )
    build(
        "report.html", "report_offline.html",
        {"/*__SKIN_CSS__*/": skin, "/*__ECHARTS__*/": echarts, "/*__UG_DATA__*/null": data},
    )
    build("form.html", "form_offline.html", {"/*__SKIN_CSS__*/": skin})


if __name__ == "__main__":
    main()
