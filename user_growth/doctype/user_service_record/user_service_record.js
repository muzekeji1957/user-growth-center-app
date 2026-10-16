// -*- js -*-
// 用户服务单据 · 表单增强脚本
// 1) 服务动作联动（流失时必须填写流失信息）
// 2) 客户历史透视（复购/流失一键查看）
// 3) 一键跳转增长大屏

const CHURN_REASON_OPTIONS = [
	"价格偏高",
	"效果不符预期",
	"服务到期未续",
	"转投竞品",
	"自身业务调整",
	"失联无响应",
	"产品下架",
	"其他",
];

frappe.ui.form.on("User Service Record", {
	refresh(frm) {
		render_customer_insight(frm);

		if (!frm.is_new()) {
			frm.add_custom_button(__("标记流失"), () => open_churn_dialog(frm), __("增长操作"));
			frm.add_custom_button(
				__("同客户全部单据"),
				() => {
					frappe.set_route("List", "User Service Record", { customer_code: frm.doc.customer_code });
				},
				__("增长操作")
			);
		}
		frm.add_custom_button(
			__("打开增长大屏"),
			() => {
				frappe.set_route("user-growth-dashboard");
			},
			__("增长操作")
		);
	},

	service_type(frm) {
		if (frm.doc.service_type === "流失") {
			frm.set_value("status", "已流失");
			if (!frm.doc.churn_date) {
				frm.set_value("churn_date", frappe.datetime.get_today());
			}
			frappe.show_alert({
				message: __("流失单据需要填写流失日期与流失原因，否则无法提交"),
				indicator: "orange",
			});
		} else if (frm.doc.status === "已流失") {
			frm.set_value("status", "有效");
		}
	},

	product(frm) {
		if (!frm.doc.product) return;
		frappe.db.get_value("Growth Product", frm.doc.product, ["category", "price", "billing_cycle"]).then((r) => {
			const v = r.message || {};
			if (v.category) frm.set_value("product_line", v.category);
			if (!frm.doc.amount && v.price) frm.set_value("amount", v.price);
			if (v.billing_cycle && !frm.doc.billing_cycle) frm.set_value("billing_cycle", v.billing_cycle);
		});
	},

	service_start(frm) {
		compute_lifetime(frm);
	},

	churn_date(frm) {
		compute_lifetime(frm);
	},
});

frappe.ui.form.on("User Service Item", {
	qty(frm, cdt, cdn) {
		item_amount(frm, cdt, cdn);
	},
	rate(frm, cdt, cdn) {
		item_amount(frm, cdt, cdn);
	},
});

function item_amount(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	row.amount = flt(row.qty || 1) * flt(row.rate || 0);
	frm.refresh_field("service_items");
	sum_items(frm);
}

function sum_items(frm) {
	let total = 0;
	(frm.doc.service_items || []).forEach((row) => {
		total += flt(row.amount || 0);
	});
	if (frm.doc.service_items && frm.doc.service_items.length && total > 0) {
		frm.set_value("amount", total);
	}
}

function compute_lifetime(frm) {
	if (!frm.doc.service_start) return;
	const end =
		frm.doc.service_type === "流失" && frm.doc.churn_date
			? frm.doc.churn_date
			: frm.doc.last_active_on || frappe.datetime.get_today();
	frm.set_value("lifetime_days", Math.max(frappe.datetime.get_day_diff(end, frm.doc.service_start), 0));
}

function open_churn_dialog(frm) {
	const d = new frappe.ui.Dialog({
		title: __("标记流失"),
		fields: [
			{
				fieldname: "churn_reason",
				fieldtype: "Select",
				label: __("流失原因"),
				options: CHURN_REASON_OPTIONS,
				reqd: 1,
				default: frm.doc.churn_reason || "服务到期未续",
			},
			{
				fieldname: "churn_date",
				fieldtype: "Date",
				label: __("流失日期"),
				reqd: 1,
				default: frm.doc.churn_date || frappe.datetime.get_today(),
			},
			{
				fieldname: "winback_score",
				fieldtype: "Int",
				label: __("召回可能性(0-100)"),
				default: frm.doc.winback_score || 50,
			},
			{
				fieldname: "churn_detail",
				fieldtype: "Small Text",
				label: __("流失说明"),
				default: frm.doc.churn_detail || "",
			},
		],
		primary_action_label: __("确认流失"),
		primary_action(values) {
			frm.call("mark_as_churned", values).then(() => {
				d.hide();
				frm.reload_doc();
				frappe.show_alert({ message: __("已标记为流失"), indicator: "red" });
			});
		},
	});
	d.show();
}

function render_customer_insight(frm) {
	if (!frm.doc.customer_code) return;
	frappe.call({
		method: "user_growth.api.get_customer_profile",
		args: { customer_code: frm.doc.customer_code, exclude: frm.doc.name },
		callback(r) {
			const p = r.message;
			if (!p || !p.total_records) return;
			const total = p.total_records + (frm.is_new() ? 1 : 0);
			frm.dashboard.add_indicator(
				__("该客户历史单据 {0} 张", [total]),
				total > 1 ? "blue" : "gray"
			);
			frm.dashboard.add_indicator(
				__("累计服务金额 {0}", [format_currency(p.total_amount || 0)]),
				p.total_amount > 1000 ? "green" : "gray"
			);
			if (p.lost_count > 0) {
				frm.dashboard.add_indicator(__("曾流失 {0} 次", [p.lost_count]), "red");
			} else {
				frm.dashboard.add_indicator(__("无流失记录"), "green");
			}
		},
	});
}
