# -*- coding: utf-8 -*-
"""纯 Python 增长分析聚合层（不依赖 Frappe）。

设计意图
--------
同一套口径被三处复用：
    1. Frappe 报表      user_growth/user_growth/report/user_growth_report/user_growth_report.py
    2. Frappe 大屏接口  user_growth/api.py
    3. 离线预览生成器   preview 生成脚本
这样"报表看到的数字"和"大屏看到的数字"永远一致，不会出现两套口径打架。

口径约定（重要）
----------------
* 新增客户：某客户**首条"新开通"单据**所在月份计 1，后续续费/升级不再重复计为新客。
* 流失客户：以"流失单据"的 churn_date 所在月份计 1。
* 期末存量：累计新增 − 累计流失（逐月滚动）。
* 收入：新开通 + 续费 + 升级 三类单据金额合计；流失单不计收入。
* 只统计已提交单据（docstatus = 1），草稿不入账。
"""

from __future__ import annotations

import datetime as _dt
from collections import OrderedDict


# --------------------------------------------------------------------------
# 工具
# --------------------------------------------------------------------------
def to_str(v):
	"""把 date / datetime / str 统一成 'YYYY-MM-DD'。"""
	if not v:
		return None
	if isinstance(v, str):
		return v[:10]
	if isinstance(v, (_dt.date, _dt.datetime)):
		return v.strftime("%Y-%m-%d")
	return str(v)[:10]


def month_key(d):
	s = to_str(d)
	return s[:7] if s else None


def shift_month(ym, delta):
	"""'2026-01' + (-1) -> '2025-12'"""
	y, m = int(ym[:4]), int(ym[5:7])
	total = (y * 12 + (m - 1)) + delta
	return "%04d-%02d" % (total // 12, total % 12 + 1)


def month_range(end_ym, months):
	"""返回截止到 end_ym 的 months 个月份列表（升序）。"""
	return [shift_month(end_ym, -(months - 1 - i)) for i in range(months)]


def pct(numerator, denominator, digits=1):
	if not denominator:
		return 0.0
	return round(numerator * 100.0 / denominator, digits)


def _safe_div(a, b, digits=2):
	if not b:
		return 0.0
	return round(float(a) / float(b), digits)


# --------------------------------------------------------------------------
# 月度趋势
# --------------------------------------------------------------------------
def first_seen_map(records):
	"""客户 -> 首次开通月份。"""
	first = {}
	for r in records:
		if r.get("service_type") != "新开通":
			continue
		code = r.get("customer_code")
		mk = month_key(r.get("service_start"))
		if not code or not mk:
			continue
		if code not in first or mk < first[code]:
			first[code] = mk
	return first


def monthly_trend(records, end_ym=None, months=13):
	"""生成月度增长趋势（含期初/期末/流失率/环比）。"""
	all_months = [month_key(r.get("service_start")) for r in records]
	all_months += [month_key(r.get("churn_date")) for r in records]
	all_months = [m for m in all_months if m]
	if not all_months:
		return []
	end_ym = end_ym or max(all_months)
	periods = month_range(end_ym, months)

	first = first_seen_map(records)
	new_map = {}
	for code, mk in first.items():
		new_map[mk] = new_map.get(mk, 0) + 1

	renew_map, upgrade_map, churn_map, revenue_map = {}, {}, {}, {}
	churn_rev_map = {}
	for r in records:
		st = r.get("service_type")
		amt = float(r.get("amount") or 0)
		if st == "续费":
			k = month_key(r.get("service_start"))
			renew_map[k] = renew_map.get(k, 0) + 1
			revenue_map[k] = revenue_map.get(k, 0.0) + amt
		elif st == "升级":
			k = month_key(r.get("service_start"))
			upgrade_map[k] = upgrade_map.get(k, 0) + 1
			revenue_map[k] = revenue_map.get(k, 0.0) + amt
		elif st == "流失":
			k = month_key(r.get("churn_date"))
			churn_map[k] = churn_map.get(k, 0) + 1
			if k:
				churn_rev_map[k] = churn_rev_map.get(k, 0.0) + amt
		elif st == "新开通":
			k = month_key(r.get("service_start"))
			revenue_map[k] = revenue_map.get(k, 0.0) + amt

	trend = []
	closing = 0
	prev_new = None
	for mk in periods:
		opening = closing
		new = new_map.get(mk, 0)
		churn = churn_map.get(mk, 0)
		closing = opening + new - churn
		trend.append(
			{
				"period": mk,
				"opening": opening,
				"new": new,
				"renew": renew_map.get(mk, 0),
				"upgrade": upgrade_map.get(mk, 0),
				"churn": churn,
				"net": new - churn,
				"closing": closing,
				"revenue": round(revenue_map.get(mk, 0.0), 2),
				"churn_rate": pct(churn, opening if opening else None) if opening else 0.0,
				"net_growth_rate": pct(new - churn, opening if opening else None) if opening else 0.0,
				"new_mom": pct(new - prev_new, prev_new) if prev_new else None,
				"churned_revenue": round(churn_rev_map.get(mk, 0.0), 2),
			}
		)
		prev_new = new
	return trend


# --------------------------------------------------------------------------
# 维度分析
# --------------------------------------------------------------------------
def dimension_breakdown(records, field, labels=None):
	"""按任意字段（channel / product_line / region）做维度聚合。"""
	buckets = OrderedDict()
	customer_seen = {}
	for r in records:
		key = r.get(field) or "未填写"
		b = buckets.setdefault(
			key,
			{
				"name": key, "customers": set(), "orders": 0,
				"revenue": 0.0, "churned": 0, "new": 0, "renew": 0,
			},
		)
		code = r.get("customer_code")
		st = r.get("service_type")
		if st == "流失":
			b["churned"] += 1
		else:
			b["orders"] += 1
			b["revenue"] += float(r.get("amount") or 0)
			if st == "新开通":
				b["new"] += 1
			elif st == "续费":
				b["renew"] += 1
		if code:
			b["customers"].add(code)
			customer_seen.setdefault(key, set()).add(code)

	total_customers = sum(len(v["customers"]) for v in buckets.values()) or 1
	total_revenue = sum(v["revenue"] for v in buckets.values()) or 1

	rows = []
	for key, v in buckets.items():
		cust = len(v["customers"])
		rows.append(
			{
				"name": key,
				"customers": cust,
				"customer_share": pct(cust, total_customers),
				"orders": v["orders"],
				"revenue": round(v["revenue"], 2),
				"revenue_share": pct(v["revenue"], total_revenue),
				"avg_amount": _safe_div(v["revenue"], v["orders"]),
				"churned": v["churned"],
				"churn_rate": pct(v["churned"], cust),
				"net": cust - v["churned"],
			}
		)
	rows.sort(key=lambda x: (-x["customers"], -x["revenue"]))
	return rows


def churn_reason_breakdown(records):
	total = 0
	buckets = {}
	for r in records:
		if r.get("service_type") != "流失":
			continue
		reason = r.get("churn_reason") or "未填写"
		buckets[reason] = buckets.get(reason, 0) + 1
		total += 1
	rows = [
		{"name": k, "value": v, "share": pct(v, total)} for k, v in buckets.items()
	]
	rows.sort(key=lambda x: -x["value"])
	return rows


def product_ranking(records, limit=10):
	agg = {}
	for r in records:
		if r.get("service_type") == "流失":
			continue
		name = r.get("product") or r.get("product_line") or "未填写"
		a = agg.setdefault(name, {"name": name, "orders": 0, "revenue": 0.0, "customers": set()})
		a["orders"] += 1
		a["revenue"] += float(r.get("amount") or 0)
		if r.get("customer_code"):
			a["customers"].add(r["customer_code"])
	rows = [
		{
			"name": v["name"],
			"orders": v["orders"],
			"revenue": round(v["revenue"], 2),
			"customers": len(v["customers"]),
			"avg_amount": _safe_div(v["revenue"], v["orders"]),
		}
		for v in agg.values()
	]
	rows.sort(key=lambda x: -x["revenue"])
	return rows[:limit]


def funnel(records):
	"""新增 -> 激活 -> 复购 -> 沉默 -> 流失"""
	new_customers = set(first_seen_map(records).keys())
	renewed = set()
	silent = set()
	churned = set()
	active = set()
	for r in records:
		code = r.get("customer_code")
		st = r.get("service_type")
		if not code:
			continue
		if st == "流失":
			churned.add(code)
		elif st in ("续费", "升级"):
			renewed.add(code)
		elif st == "新开通":
			active.add(code)
		if st != "流失" and r.get("activity_score") is not None:
			if (r.get("activity_score") or 0) < 40:
				silent.add(code)
	active -= churned
	return [
		{"name": "累计获客", "value": len(new_customers)},
		{"name": "已激活", "value": len(new_customers)},
		{"name": "产生复购", "value": len(renewed)},
		{"name": "低活跃预警", "value": len(silent - churned)},
		{"name": "当前在服", "value": len(active)},
		{"name": "累计流失", "value": len(churned)},
	]


def recent_activities(records, limit=20):
	def _dt_key(r):
		return to_str(r.get("churn_date") or r.get("service_start")) or ""

	rows = [r for r in records if _dt_key(r)]
	rows.sort(key=_dt_key, reverse=True)
	out = []
	for r in rows[:limit]:
		out.append(
			{
				"date": _dt_key(r),
				"customer": r.get("customer_name"),
				"type": r.get("service_type"),
				"product": r.get("product") or r.get("product_line"),
				"amount": float(r.get("amount") or 0),
				"channel": r.get("channel"),
				"region": r.get("region"),
				"reason": r.get("churn_reason"),
			}
		)
	return out


def kpi_summary(records, trend):
	first = first_seen_map(records)
	total_customers = len(first)
	last = trend[-1] if trend else {}
	prev = trend[-2] if len(trend) > 1 else {}

	revenue = 0.0
	orders = 0
	lifetimes = []
	winback_pool = 0
	key_accounts = set()
	for r in records:
		st = r.get("service_type")
		if st == "流失":
			winback_pool += 1 if r.get("is_winback") else 0
			if r.get("lifetime_days"):
				lifetimes.append(float(r["lifetime_days"]))
			continue
		revenue += float(r.get("amount") or 0)
		orders += 1
		if r.get("is_key_account"):
			key_accounts.add(r.get("customer_code"))

	churn_total = sum(t["churn"] for t in trend)
	return {
		"total_customers": total_customers,
		"active_customers": last.get("closing", 0),
		"month_new": last.get("new", 0),
		"month_new_mom": last.get("new_mom"),
		"month_churn": last.get("churn", 0),
		"month_churn_mom": pct(
			last.get("churn", 0) - prev.get("churn", 0), prev.get("churn", 0)
		) if prev.get("churn") else None,
		"month_net": last.get("net", 0),
		"churn_rate": last.get("churn_rate", 0.0),
		"net_growth_rate": last.get("net_growth_rate", 0.0),
		"total_revenue": round(revenue, 2),
		"avg_amount": _safe_div(revenue, orders),
		"total_orders": orders,
		"churn_total": churn_total,
		"avg_lifetime": round(sum(lifetimes) / len(lifetimes), 1) if lifetimes else 0,
		"winback_pool": winback_pool,
		"key_accounts": len(key_accounts),
	}


def insight(kpi, trend, churn_rows, dimension_rows):
	"""规则式一句话解读（不调用模型，可替换为 LLM 输出）。"""
	if not trend:
		return "暂无数据"
	last = trend[-1]
	parts = []
	parts.append(
		"本期新增客户 %d 家，流失 %d 家，净增 %d 家，期末在服 %d 家。"
		% (last["new"], last["churn"], last["net"], last["closing"])
	)
	mom = last.get("new_mom")
	if mom is not None:
		parts.append("新增环比%s%.1f%%。" % ("上升" if mom >= 0 else "下降", abs(mom)))
	parts.append("当月流失率 %.1f%%，平均客单价 %.0f 元。" % (last["churn_rate"], kpi.get("avg_amount", 0)))
	if churn_rows:
		parts.append("流失主因是「%s」（占 %.0f%%）。" % (churn_rows[0]["name"], churn_rows[0]["share"]))
	if dimension_rows:
		best = min(dimension_rows, key=lambda x: x["churn_rate"])
		worst = max(dimension_rows, key=lambda x: x["churn_rate"])
		parts.append(
			"渠道表现：%s 留存最好（流失率 %.1f%%），%s 需重点干预（%.1f%%）。"
			% (best["name"], best["churn_rate"], worst["name"], worst["churn_rate"])
		)
	if kpi.get("winback_pool"):
		parts.append("可召回客户 %d 家，建议本月启动召回。" % kpi["winback_pool"])
	return "".join(parts)


# --------------------------------------------------------------------------
# v1.1 借鉴扩展（对标：Gainsight/ChurnZero 健康分 · 神策/Coale RFM · 同期群留存 · Playbook 预警）
# --------------------------------------------------------------------------
def _recency_score(days):
	"""新近度打分：越久没动 = 越不健康。"""
	if days <= 7:
		return 100.0
	if days <= 30:
		return 90.0
	if days <= 60:
		return 75.0
	if days <= 90:
		return 60.0
	if days <= 180:
		return 40.0
	return 20.0


def _health_level(score):
	if score >= 80:
		return "健康"
	if score >= 60:
		return "观察"
	if score >= 40:
		return "风险"
	return "高危"


def _percentile_scores(values):
	"""数值 -> 0~100 百分位分（并列同分）。"""
	if not values:
		return {}
	sv = sorted(values)
	n = len(sv)
	first_idx = {}
	for i, v in enumerate(sv):
		if v not in first_idx:
			first_idx[v] = i
	return {v: round(i * 100.0 / max(n - 1, 1), 1) for v, i in first_idx.items()}


def customer_health(records, as_of=None):
	"""客户健康分（借鉴 Gainsight / ChurnZero 健康评分模型）。

	综合分 = 新近度30% + 消费力30% + 频次25% + 活跃度15%（0~100）。
	已流失客户按上限 35 分计（已流失不再是"干预对象"，风险榜只看在服客户）。
	返回按分数降序的全量客户列表。
	"""
	stats = {}
	last_day = ""
	for r in records:
		code = r.get("customer_code")
		if not code:
			continue
		s = stats.setdefault(
			code,
			{
				"customer_code": code,
				"customer": r.get("customer_name") or code,
				"region": r.get("region"),
				"channel": r.get("channel"),
				"revenue": 0.0, "orders": 0,
				"last": "", "churned": False, "acts": [],
			},
		)
		st = r.get("service_type")
		d = to_str(r.get("service_start")) or ""
		if st == "流失":
			s["churned"] = True
			cd = to_str(r.get("churn_date")) or d
			if cd > s["last"]:
				s["last"] = cd
		else:
			s["revenue"] += float(r.get("amount") or 0)
			s["orders"] += 1
			if r.get("activity_score") is not None:
				s["acts"].append(float(r["activity_score"]))
			if d > s["last"]:
				s["last"] = d
		if d > last_day:
			last_day = d

	as_of = as_of or last_day
	if not as_of:
		return []
	as_of_dt = _dt.date(int(as_of[:4]), int(as_of[5:7]), int(as_of[8:10]))

	def days_since(d):
		if not d:
			return 9999
		return (as_of_dt - _dt.date(int(d[:4]), int(d[5:7]), int(d[8:10]))).days

	m_scores = _percentile_scores([s["revenue"] for s in stats.values()])
	f_scores = _percentile_scores([float(s["orders"]) for s in stats.values()])

	rows = []
	for code, s in stats.items():
		act = sum(s["acts"]) / len(s["acts"]) if s["acts"] else 50.0
		rec = days_since(s["last"])
		score = (
			_recency_score(rec) * 0.30
			+ m_scores.get(s["revenue"], 50.0) * 0.30
			+ f_scores.get(float(s["orders"]), 50.0) * 0.25
			+ act * 0.15
		)
		if s["churned"]:
			score = min(score * 0.35, 35.0)
		score = round(score, 1)
		rows.append(
			{
				"customer_code": code,
				"customer": s["customer"],
				"region": s["region"],
				"channel": s["channel"],
				"revenue": round(s["revenue"], 2),
				"orders": s["orders"],
				"last_date": s["last"],
				"recency_days": rec,
				"activity": round(act, 1),
				"churned": s["churned"],
				"score": score,
				"level": _health_level(score),
			}
		)
	rows.sort(key=lambda x: -x["score"])
	return rows


def rfm_summary(health_rows):
	"""RFM 客户分层（借鉴神策 / Coale-Insights）。

	R=新近度(越近越好) F=频次 M=消费额，各按五分位打 1~5 分后映射 6 个价值段。
	"""
	if not health_rows:
		return {"segments": [], "points": []}
	r_vals = [h["recency_days"] for h in health_rows]
	f_vals = [float(h["orders"]) for h in health_rows]
	m_vals = [h["revenue"] for h in health_rows]

	def score_fn(vals, higher_better=True):
		sv = sorted(set(vals))
		n = len(sv)

		def sc(v):
			i = sv.index(v)
			p = i * 5 // max(n - 1, 1) + 1  # 1..5
			return p if higher_better else 6 - p

		return sc

	rsc, fsc, msc = score_fn(r_vals, False), score_fn(f_vals), score_fn(m_vals)

	SEG_ORDER = ["重要价值", "重要发展", "重要挽留", "重要召回", "一般保持", "流失警告"]
	counts = {k: 0 for k in SEG_ORDER}
	points = []
	for h in health_rows:
		R, F, M = rsc(h["recency_days"]), fsc(float(h["orders"])), msc(h["revenue"])
		if R >= 4 and F >= 4:
			seg = "重要价值"
		elif R >= 4 and M >= 4:
			seg = "重要发展"
		elif R >= 4:
			seg = "一般保持"
		elif F >= 4:
			seg = "重要挽留"
		elif M >= 4:
			seg = "重要召回"
		else:
			seg = "流失警告"
		counts[seg] += 1
		points.append(
			[h["recency_days"], round(h["revenue"], 2), h["orders"], h["customer"], seg]
		)

	total = len(health_rows) or 1
	segments = [
		{"name": k, "value": v, "share": pct(v, total)} for k, v in counts.items()
	]
	return {"segments": segments, "points": points}


def retention_curve(records, cohorts=6):
	"""同期群留存曲线（借鉴神策 / GrowingIO 留存模型）。

	按客户首次开通月分组，跟踪每一组随月份推移的留存率（%），观察产品粘性。
	"""
	first = first_seen_map(records)
	churn_m = {}
	for r in records:
		if r.get("service_type") == "流失" and r.get("customer_code"):
			m = month_key(r.get("churn_date"))
			code = r["customer_code"]
			if m and (code not in churn_m or m > churn_m[code]):
				churn_m[code] = m
	if not first:
		return []
	cohort_months = sorted(set(first.values()))[-cohorts:]
	all_months = [month_key(r.get("service_start")) for r in records]
	all_months += list(churn_m.values())
	end_ym = max([m for m in all_months if m], default=cohort_months[-1])

	rows = []
	for m in cohort_months:
		cust = [c for c, mk in first.items() if mk == m]
		size = len(cust)
		if not size:
			continue
		points = []
		for k in range(0, 13):
			mk = shift_month(m, k)
			if mk > end_ym:
				break
			alive = [c for c in cust if c not in churn_m or churn_m[c] >= mk]
			points.append([k, pct(len(alive), size)])
		rows.append({"cohort": m, "size": size, "points": points})
	return rows


def growth_alerts(kpi, trend, channels, health_rows):
	"""增长预警 + 行动建议（借鉴 ChurnZero：预警不止提示，还给出 Playbook）。

	规则式、阈值可调；level=高(红)/中(黄)。返回按严重度排序的告警列表。
	"""
	alerts = []
	if not trend:
		return alerts
	last = trend[-1]
	if last["churn_rate"] >= 8:
		alerts.append({
			"level": "高", "icon": "🔴",
			"title": "当月流失率 %.1f%%，已超 8%% 警戒线" % last["churn_rate"],
			"action": "48 小时内启动流失客户回访，按流失原因分派跟进责任人",
		})
	elif last["churn_rate"] >= 5:
		alerts.append({
			"level": "中", "icon": "🟡",
			"title": "当月流失率 %.1f%%，接近 8%% 警戒线" % last["churn_rate"],
			"action": "筛出本月流失客户，一周内完成电话回访并记录原因",
		})

	prev = trend[-2] if len(trend) > 1 else None
	if prev and prev.get("new") and last["new"] < prev["new"] * 0.8:
		alerts.append({
			"level": "中", "icon": "🟡",
			"title": "新增客户环比下滑 %.0f%%（%d → %d 家）" % (
				abs(last["new_mom"] or 0), prev["new"], last["new"]),
			"action": "复盘获客漏斗：检查各渠道线索量与转化率，补投效果最好的渠道",
		})

	active = [h for h in (health_rows or []) if not h["churned"]]
	if active:
		top20 = sorted(active, key=lambda x: -x["revenue"])[: max(1, len(active) // 5)]
		danger = [h for h in top20 if h["score"] < 60]
		if danger:
			alerts.append({
				"level": "高", "icon": "🔴",
				"title": "%d 家高价值客户健康分低于 60（如 %s）" % (
					len(danger), danger[0]["customer"]),
				"action": "指派客户成功经理 1对1 挽留，优先处理健康分最低的 5 家",
			})

	low_act = [h for h in active if h["activity"] < 40]
	if len(low_act) >= max(3, int(len(active) * 0.1)):
		alerts.append({
			"level": "中", "icon": "🟡",
			"title": "%d 家在服客户活跃度低于 40 分" % len(low_act),
			"action": "推送会员权益/免费培训活动触达，两周内未激活转入人工跟进",
		})

	if channels:
		worst = max(channels, key=lambda x: x["churn_rate"])
		if worst["churn_rate"] >= 25:
			alerts.append({
				"level": "中", "icon": "🟡",
				"title": "渠道「%s」流失率 %.1f%%，为全部渠道最高" % (
					worst["name"], worst["churn_rate"]),
				"action": "复盘该渠道获客质量，调整投放策略或销售话术",
			})

	alerts.sort(key=lambda a: 0 if a["level"] == "高" else 1)
	return alerts


def build_dashboard_payload(records, months=13, end_ym=None):
	"""大屏一次性需要的全部数据。"""
	trend = monthly_trend(records, end_ym=end_ym, months=months)
	kpi = kpi_summary(records, trend)
	channels = dimension_breakdown(records, "channel")
	lines = dimension_breakdown(records, "product_line")
	regions = dimension_breakdown(records, "region")
	churns = churn_reason_breakdown(records)
	products = product_ranking(records, limit=10)
	fn = funnel(records)
	acts = recent_activities(records, limit=24)

	# v1.1 扩展：健康分 / RFM / 留存 / 预警
	health_rows = customer_health(records, as_of=end_ym and (end_ym + "-28"))
	active_rows = [h for h in health_rows if not h["churned"]]
	level_counts = {"健康": 0, "观察": 0, "风险": 0, "高危": 0}
	for h in active_rows:
		level_counts[h["level"]] = level_counts.get(h["level"], 0) + 1
	risk_list = sorted(active_rows, key=lambda x: x["score"])[:10]
	health = {
		"avg_active": round(sum(h["score"] for h in active_rows) / len(active_rows), 1)
		if active_rows else 0.0,
		"levels": level_counts,
		"at_risk": level_counts.get("风险", 0) + level_counts.get("高危", 0),
		"risk_list": risk_list,
	}
	rfm = rfm_summary(health_rows)
	retention = retention_curve(records)
	alerts = growth_alerts(kpi, trend, channels, health_rows)

	return {
		"kpi": kpi,
		"trend": trend,
		"channels": channels,
		"product_lines": lines,
		"regions": regions,
		"churn_reasons": churns,
		"products": products,
		"funnel": fn,
		"activities": acts,
		"insight": insight(kpi, trend, churns, channels),
		# v1.1
		"health": health,
		"rfm": rfm,
		"retention": retention,
		"alerts": alerts,
	}
