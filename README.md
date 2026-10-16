# user_growth · 用户增长中心

Frappe 自定义 App，包含三件交付物：

1. **用户服务单据（User Service Record）** —— 可提交的业务单据，记录用户服务的
   新开通 / 续费 / 升级 / 流失，含客户健康度与流失归因字段，内置校验规则与
   789 条可复现演示数据。
2. **用户增长分析报表（User Growth Report）** —— Script Report，提供
   月度趋势 / 渠道维度 / 产品线维度 / 区域维度四种视图，含图表与摘要卡。
3. **用户增长数据大屏（user-growth-dashboard）** —— ECharts 大屏页面，
   KPI 卡、趋势、流失率、渠道/产品/区域分布、漏斗、实时动态，
   支持浅色/深色主题切换与定时自动刷新。

## 环境要求

- Frappe Framework v14 / v15（bench 环境）
- Python >= 3.10
- 无需 ERPNext，无其他依赖

## 安装

```bash
# 1. 进入 bench 目录
cd frappe-bench

# 2. 获取 App（本地路径安装）
bench get-app /path/to/user_growth

# 3. 安装到站点
bench --site your-site.local install-app user_growth

# 4. （可选）灌入演示数据：789 条已提交的服务单据
bench --site your-site.local execute user_growth.seed.mock_data.seed
```

安装时 `after_install` 会自动完成：

- 创建自定义角色 **Growth Analyst（增长分析师）**
- 创建 **用户增长中心** Workspace（工作台入口）
- 写入 **20 个产品主数据**（复用真实在售产品，价格锚点 9.9 → 9999）

## 使用入口

| 交付物 | 入口 |
|--------|------|
| 服务单据 | `/app/user-service-record` |
| 分析报表 | `/app/query-report/User Growth Report` |
| 数据大屏 | `/app/user-growth-dashboard`（支持 `?theme=dark` 深色） |

## 数据口径（重要）

- 只统计 **已提交**（docstatus = 1）的单据，草稿不入账。
- 新增客户 = 首条「新开通」单据所在月；流失 = 流失单据 churn_date 所在月。
- 期末存量 = 累计新增 − 累计流失（逐月滚动）。
- 报表与大屏共用同一套聚合层（`user_growth/analytics.py`），数字永远一致。

## 离线预览（无需安装 Frappe）

`preview/dashboard_offline.html` 为自包含大屏预览，双击即可打开；
`preview/report_offline.html`、`preview/form_offline.html` 为报表与表单的
界面预览。重新生成：

```bash
python preview/generate_mock_data.py 420
python preview/build_offline.py
```
