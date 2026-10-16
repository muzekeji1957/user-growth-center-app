// -*- js -*-
// 用户增长数据大屏 · 客户端渲染
// 设计：环境无关。在 Frappe 内通过 frappe.call 取数；离线预览时 fetch 本地 JSON。
// 同一份渲染逻辑同时服务 Frappe Page 与离线 HTML 预览。

// 命名空间：环境无关（Frappe 内等价于 frappe.provide("user_growth")）
window.user_growth = window.user_growth || {};

(function () {
	const C = {
		primary: "#16B1A7",
		accent: "#FF6A2C",
		good: "#1AA260",
		warn: "#F2A33C",
		bad: "#E0533D",
		blue: "#5078FF",
	};

	function load_echarts(cb) {
		if (window.echarts) return cb();
		if (window.frappe) {
			frappe.require("/assets/user_growth/js/echarts.min.js", cb);
			return;
		}
		const s = document.createElement("script");
		s.src = "echarts.min.js";
		s.onload = cb;
		s.onerror = function () {
			console.error("echarts 加载失败");
		};
		document.head.appendChild(s);
	}

	function fetch_data(cb) {
		// 离线预览：数据被内联进 HTML（window.UG_DATA），双击即可用，无需本地服务器。
		if (window.UG_DATA) return cb(window.UG_DATA);
		if (window.frappe) {
			frappe.call({
				method: "user_growth.api.get_growth_dashboard",
				args: { months: 13 },
				callback: (r) => cb(r.message),
			});
			return;
		}
		fetch("mock_data.json")
			.then((r) => r.json())
			.then(cb)
			.catch(() => console.error("mock_data.json 读取失败"));
	}

	function init_theme() {
		const root = document.getElementById("dashboard-root");
		// 支持 ?theme=dark 直达深色（大屏投放/演示用），本地记忆优先级其次
		const qp = new URLSearchParams(location.search).get("theme");
		const dark = qp ? qp === "dark" : localStorage.getItem("ug_dark") === "1";
		root.classList.toggle("ug-dark", dark);
		const btn = document.getElementById("ug-theme");
		if (btn)
			btn.textContent = dark ? "切换浅色" : "切换深色";
		return dark;
	}

	function render_kpis(k, health) {
		const mom = k.month_new_mom;
		const momTxt =
			mom == null ? "—" : (mom >= 0 ? "▲ " : "▼ ") + Math.abs(mom).toFixed(1) + "% 环比";
		const cmom = k.month_churn_mom;
		const cmomTxt =
			cmom == null ? "—" : (cmom >= 0 ? "▲ " : "▼ ") + Math.abs(cmom).toFixed(1) + "% 环比";
		const cards = [
			{ v: k.active_customers, l: "期末在服客户", d: "净增长率 " + (k.net_growth_rate || 0).toFixed(1) + "%", c: "ug-up" },
			{ v: k.month_new, l: "本月新增", d: momTxt, c: mom >= 0 ? "ug-up" : "ug-down" },
			{ v: k.month_churn, l: "本月流失", d: cmomTxt, c: cmom > 0 ? "ug-down" : "ug-up" },
			{ v: "¥" + fmt(k.total_revenue), l: "累计营收", d: "客单价 ¥" + fmt(k.avg_amount), c: "" },
			{ v: (k.churn_rate || 0).toFixed(1) + "%", l: "当月流失率", d: "累计流失 " + k.churn_total, c: "ug-down" },
			{ v: k.winback_pool, l: "可召回客户", d: "重点客户 " + k.key_accounts, c: k.winback_pool ? "ug-up" : "" },
		];
		if (health) {
			cards.push({ v: health.avg_active, l: "平均健康分", d: "在服客户均值 / 100", c: health.avg_active >= 60 ? "ug-up" : "ug-down" });
			cards.push({ v: health.at_risk, l: "风险客户", d: "风险+高危待干预", c: health.at_risk ? "ug-down" : "ug-up" });
		}
		document.getElementById("ug-kpis").innerHTML = cards
			.map(
				(x) =>
					'<div class="ug-kpi"><div class="v">' +
					x.v +
					'</div><div class="l">' +
					x.l +
					'</div><div class="d ' +
					x.c +
					'">' +
					x.d +
					"</div></div>"
			)
			.join("");
	}

	function fmt(n) {
		n = Number(n) || 0;
		if (n >= 10000) return (n / 10000).toFixed(1) + "万";
		return Math.round(n).toLocaleString("zh-CN");
	}

	function chart(id, option) {
		const el = document.getElementById(id);
		if (!el) return;
		const inst = echarts.getInstanceByDom(el) || echarts.init(el);
		inst.setOption(option, true);
		return inst;
	}

	const AXIS = (dark) => ({
		axisLine: { lineStyle: { color: dark ? "#3a4a5e" : "#cfd8e3" } },
		axisLabel: { color: dark ? "#9fb0c2" : "#6B7785" },
		splitLine: { lineStyle: { color: dark ? "#22303f" : "#eef2f7" } },
	});

	function render_trend(trend, dark) {
		chart("ug-trend", {
			color: [C.blue, C.good, C.bad, C.accent],
			tooltip: { trigger: "axis" },
			legend: { textStyle: { color: dark ? "#cdd9e5" : "#444" }, top: 0 },
			grid: { left: 50, right: 60, top: 36, bottom: 30 },
			xAxis: { type: "category", data: trend.map((t) => t.period), ...AXIS(dark) },
			yAxis: [
				{ type: "value", name: "客户数", ...AXIS(dark) },
				{ type: "value", name: "营收", ...AXIS(dark) },
			],
			series: [
				{ name: "期末存量", type: "line", smooth: true, data: trend.map((t) => t.closing), areaStyle: { opacity: 0.08 } },
				{ name: "新增", type: "bar", data: trend.map((t) => t.new) },
				{ name: "流失", type: "bar", data: trend.map((t) => t.churn) },
				{ name: "营收(元)", type: "line", yAxisIndex: 1, smooth: true, data: trend.map((t) => t.revenue) },
			],
		});
	}

	function render_churn_rate(trend, dark) {
		chart("ug-churn-rate", {
			color: [C.bad],
			tooltip: { trigger: "axis" },
			grid: { left: 50, right: 20, top: 30, bottom: 30 },
			xAxis: { type: "category", data: trend.map((t) => t.period), ...AXIS(dark) },
			yAxis: { type: "value", name: "流失率%", ...AXIS(dark), axisLabel: { formatter: "{value}%" } },
			series: [
				{
					type: "line",
					smooth: true,
					areaStyle: { color: "rgba(224,83,61,0.15)" },
					data: trend.map((t) => t.churn_rate),
				},
			],
		});
	}

	function render_pie(id, rows, name_key, dark, palette) {
		chart(id, {
			tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
			legend: { type: "scroll", orient: "vertical", right: 0, top: 10, textStyle: { color: dark ? "#cdd9e5" : "#444" } },
			series: [
				{
					type: "pie",
					radius: ["38%", "66%"],
					center: ["38%", "52%"],
					data: rows.map((r) => ({ name: r[name_key], value: r.value })),
					itemStyle: { borderColor: dark ? "#16202E" : "#fff", borderWidth: 2 },
				},
			],
			color: palette,
		});
	}

	function render_bar(id, rows, dark, color, vkey) {
		const top = rows.slice(0, 10);
		chart(id, {
			tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
			grid: { left: 150, right: 60, top: 20, bottom: 20 },
			xAxis: { type: "value", ...AXIS(dark) },
			yAxis: { type: "category", data: top.map((r) => r.name).reverse(), ...AXIS(dark) },
			series: [
				{
					type: "bar",
					data: top.map((r) => Math.round(r[vkey] || 0)).reverse(),
					itemStyle: { color: color, borderRadius: [0, 6, 6, 0] },
					label: { show: true, position: "right", color: dark ? "#cdd9e5" : "#555" },
				},
			],
		});
	}

	function render_funnel(fn, dark) {
		chart("ug-funnel", {
			tooltip: { trigger: "item", formatter: "{b}: {c}" },
			series: [
				{
					type: "funnel",
					left: 10,
					right: 10,
					top: 10,
					bottom: 10,
					minSize: "20%",
					sort: "descending",
					gap: 2,
					label: { show: true, position: "inside", formatter: "{b}\n{c}", color: "#fff" },
					data: fn.map((f) => ({ name: f.name, value: f.value })),
					color: [C.blue, C.primary, C.good, C.warn, C.accent, C.bad],
				},
			],
		});
	}

	// ---------------- v1.1：健康分 / RFM / 留存 / 预警 ----------------

	const SEG_COLORS = { "重要价值": "#1AA260", "重要发展": "#16B1A7", "重要挽留": "#5078FF", "重要召回": "#9b6dff", "一般保持": "#F2A33C", "流失警告": "#E0533D" };

	function render_alerts(alerts) {
		const el = document.getElementById("ug-alerts");
		if (!el) return;
		if (!alerts || !alerts.length) {
			el.innerHTML = '<div class="ug-alert ok">✅ 各项指标均在安全区间，无增长预警。</div>';
			return;
		}
		el.innerHTML = alerts
			.map(
				(a) =>
					'<div class="ug-alert ' + (a.level === "高" ? "hi" : "mid") + '">' +
					'<div class="t">' + a.icon + " " + a.title + "</div>" +
					'<div class="a">→ 行动建议：' + a.action + "</div></div>"
			)
			.join("");
	}

	function render_risk(list) {
		const el = document.getElementById("ug-risk");
		if (!el) return;
		if (!list || !list.length) { el.innerHTML = '<div class="ug-risk-empty">暂无风险客户 🎉</div>'; return; }
		el.innerHTML =
			'<div class="ug-risk-head"><span>客户</span><span>健康分</span></div>' +
			list
				.map((r) => {
					const lv = { 高危: "hp-bad", 风险: "hp-warn", 观察: "hp-mid", 健康: "hp-good" }[r.level] || "hp-mid";
					return (
						'<div class="ug-risk-row"><div class="who"><b>' + r.customer + "</b>" +
						'<small>' + (r.region || "") + " · " + (r.channel || "") + " · 停滞 " + r.recency_days + " 天</small></div>" +
						'<div class="sc"><span class="ug-hpill ' + lv + '">' + r.level + " " + r.score + "</span>" +
						'<i style="width:' + Math.max(r.score, 4) + '%"></i></div></div>'
					);
				})
				.join("");
	}

	function render_rfm(rfm, dark) {
		if (!rfm) return;
		// 六段价值分布（环形） + 客户散点（X 停滞天数 / Y 消费额 / 气泡=频次）
		chart("ug-rfm-pie", {
			tooltip: { trigger: "item", formatter: "{b}: {c} 家 ({d}%)" },
			legend: { bottom: 0, textStyle: { color: dark ? "#cdd9e5" : "#555", fontSize: 11 }, itemWidth: 12, itemHeight: 8 },
			series: [
				{
					type: "pie",
					radius: ["42%", "68%"],
					center: ["50%", "44%"],
					data: rfm.segments.map((s) => ({ name: s.name, value: s.value, itemStyle: { color: SEG_COLORS[s.name] } })),
					label: { show: false },
					itemStyle: { borderColor: dark ? "#16202E" : "#fff", borderWidth: 2 },
				},
			],
		});
		chart("ug-rfm-dot", {
			tooltip: {
				formatter: (p) =>
					p.data[3] + "<br/>停滞 " + p.data[0] + " 天 · 消费 ¥" + fmt(p.data[1]) + " · " + p.data[4],
			},
			grid: { left: 56, right: 20, top: 20, bottom: 32 },
			xAxis: { type: "value", name: "停滞天数", nameTextStyle: { color: dark ? "#9fb0c2" : "#888" }, ...AXIS(dark) },
			yAxis: { type: "value", name: "消费额", ...AXIS(dark) },
			series: Object.keys(SEG_COLORS).map((seg) => ({
				name: seg,
				type: "scatter",
				data: rfm.points.filter((p) => p[4] === seg),
				symbolSize: (d) => Math.max(6, Math.min(d[2] * 2.2, 22)),
				itemStyle: { color: SEG_COLORS[seg], opacity: 0.75 },
			})),
			legend: { bottom: 0, textStyle: { color: dark ? "#cdd9e5" : "#555", fontSize: 11 }, itemWidth: 12, itemHeight: 8 },
		});
	}

	function render_retention(retention, dark) {
		if (!retention || !retention.length) return;
		chart("ug-retention", {
			color: [C.primary, C.blue, C.accent, C.good, "#9b6dff", C.warn],
			tooltip: { trigger: "axis", formatter: (ps) => "第 " + ps[0].data[0] + " 月<br/>" + ps.map((p) => p.marker + p.seriesName + ": " + p.data[1] + "%").join("<br/>") },
			legend: { textStyle: { color: dark ? "#cdd9e5" : "#555" }, top: 0 },
			grid: { left: 50, right: 30, top: 36, bottom: 30 },
			xAxis: { type: "value", name: "开通后第 N 月", max: 12, nameTextStyle: { color: dark ? "#9fb0c2" : "#888" }, ...AXIS(dark) },
			yAxis: { type: "value", name: "留存率%", max: 100, ...AXIS(dark), axisLabel: { formatter: "{value}%" } },
			series: retention.map((c) => ({
				name: c.cohort + "（" + c.size + "家）",
				type: "line",
				smooth: true,
				data: c.points,
			})),
		});
	}

	function render_health_pie(levels, dark) {
		if (!levels) return;
		const map = [["健康", C.good], ["观察", C.blue], ["风险", C.warn], ["高危", C.bad]];
		chart("ug-healthpie", {
			tooltip: { trigger: "item", formatter: "{b}: {c} 家 ({d}%)" },
			legend: { bottom: 0, textStyle: { color: dark ? "#cdd9e5" : "#555", fontSize: 11 } },
			series: [
				{
					type: "pie",
					radius: ["42%", "68%"],
					center: ["50%", "44%"],
					data: map.map(([k, c]) => ({ name: k, value: levels[k] || 0, itemStyle: { color: c } })),
					label: { show: false },
					itemStyle: { borderColor: dark ? "#16202E" : "#fff", borderWidth: 2 },
				},
			],
		});
	}

	function render_feed(acts) {
		const el = document.getElementById("ug-feed");
		if (!el) return;
		const pill = { 新开通: "ug-t-new", 续费: "ug-t-renew", 升级: "ug-t-upgrade", 流失: "ug-t-churn" };
		el.innerHTML = acts
			.slice(0, 18)
			.map((a) => {
				const m = a.amount ? "¥" + fmt(a.amount) : "";
				const why = a.reason ? " · " + a.reason : "";
				return (
					'<div class="row"><span><span class="ug-pill ' +
					(pill[a.type] || "") +
					'">' +
					a.type +
					"</span>" +
					(a.customer || "") +
					' <span style="color:var(--ug-sub)">· ' +
					(a.product || "") +
					"</span></span><span>" +
					a.date +
					" " +
					m +
					why +
					"</span></div>"
				);
			})
			.join("");
	}

	function render(payload) {
		if (!payload) return;
		const dark = document.getElementById("dashboard-root").classList.contains("ug-dark");
		render_kpis(payload.kpi, payload.health);
		render_trend(payload.trend, dark);
		render_churn_rate(payload.trend, dark);
		render_pie("ug-channel", payload.channels, "name", dark, [C.primary, C.accent, C.good, C.blue, C.warn, C.bad, "#9b6dff", "#ff7eb6"]);
		render_bar("ug-product", payload.products, dark, C.accent, "revenue");
		render_bar("ug-region", payload.regions, dark, C.primary, "customers");
		render_pie("ug-churn-reason", payload.churn_reasons, "name", dark, ["#E0533D", "#F2A33C", "#FF6A2C", "#16B1A7", "#5078FF", "#9b6dff", "#999", "#ccc"]);
		render_funnel(payload.funnel, dark);
		render_feed(payload.activities);
		// v1.1 新模块（数据缺失时静默跳过，兼容旧缓存）
		render_alerts(payload.alerts);
		render_risk(payload.health && payload.health.risk_list);
		render_rfm(payload.rfm, dark);
		render_retention(payload.retention, dark);
		render_health_pie(payload.health && payload.health.levels, dark);
		const ins = document.getElementById("ug-insight");
		if (ins) ins.innerHTML = "<b>智能解读：</b>" + (payload.insight || "");
		const gen = document.getElementById("ug-gen");
		if (gen) gen.textContent = "数据更新：" + (payload.generated_at || "") + " · 单据 " + (payload.record_count || 0) + " 条";
	}

	function boot() {
		const root = document.getElementById("dashboard-root");
		if (!root) return;
		init_theme();
		load_echarts(function () {
			fetch_data(render);
		});
		const btn = document.getElementById("ug-theme");
		if (btn)
			btn.onclick = function () {
				const dark = !root.classList.contains("ug-dark");
				root.classList.toggle("ug-dark", dark);
				localStorage.setItem("ug_dark", dark ? "1" : "0");
				btn.textContent = dark ? "切换浅色" : "切换深色";
				fetch_data(render);
			};
		const ref = document.getElementById("ug-refresh");
		if (ref)
			ref.onclick = function () {
				fetch_data(render);
			};
		window.addEventListener("resize", function () {
			document.querySelectorAll(".ug-chart").forEach((el) => {
				const i = echarts.getInstanceByDom(el);
				if (i) i.resize();
			});
		});
	}

	if (window.frappe) {
		frappe.ready(boot);
	} else {
		document.addEventListener("DOMContentLoaded", boot);
	}

	user_growth.render_dashboard = boot;
})();
