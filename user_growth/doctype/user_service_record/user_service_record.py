# -*- coding: utf-8 -*-
"""用户服务单据（User Service Record）控制器。

单据承载用户服务的完整生命周期事件：新开通 / 续费 / 升级 / 流失。

设计要点
--------
1. **可提交单据**：草稿态不参与统计，只有 ``docstatus = 1`` 的记录才算
   "已生效的服务事件"，报表与大屏的口径因此干净可信。
2. **流失必须留痕**：``service_type == "流失"`` 时强制要求流失日期 + 流失原因，
   并把状态置为"已流失"，保证流失归因数据完整（否则报表会静默少算流失）。
3. **客户编号稳定**：同一客户多次续费复用同一 ``customer_code``，
   这是计算复购率 / 留存率的前提。
4. **生命周期自动计算**：``lifetime_days`` 用于平均在网时长与 LTV 分析。
5. **写操作即失效缓存**：任何保存都会清掉大屏快照缓存，保证大屏准实时。
"""

import hashlib

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import date_diff, flt, getdate, nowdate

DASHBOARD_CACHE_KEY = "user_growth:dashboard_snapshot"


class UserServiceRecord(Document):
	# ------------------------------------------------------------------
	# 生命周期钩子
	# ------------------------------------------------------------------
	def before_insert(self):
		self.generate_customer_code()

	def validate(self):
		self.fetch_from_product()
		self.validate_amount()
		self.validate_dates()
		self.sync_status()
		self.validate_churn()
		self.sync_lifetime()
		self.sync_items()

	def before_submit(self):
		if not self.customer_name:
			frappe.throw(_("提交前必须填写客户名称"))
		if flt(self.amount) < 0:
			frappe.throw(_("服务金额不能为负数"))
		if self.service_type == "流失" and not self.churn_date:
			frappe.throw(_("流失单据提交前必须填写流失日期"))

	def on_update(self):
		clear_dashboard_cache()

	def on_submit(self):
		clear_dashboard_cache()

	def on_cancel(self):
		clear_dashboard_cache()

	# ------------------------------------------------------------------
	# 校验 / 同步
	# ------------------------------------------------------------------
	def generate_customer_code(self):
		"""按手机号（优先）生成稳定的客户编号，保证复购可识别。"""
		if self.customer_code:
			return

		# 老客户：复用已有编号
		if self.mobile:
			existing = frappe.db.get_value(
				"User Service Record", {"mobile": self.mobile}, "customer_code"
			)
			if existing:
				self.customer_code = existing
				return

		raw = (self.mobile or self.customer_name or "").strip()
		if raw:
			digest = hashlib.md5(raw.encode("utf-8")).hexdigest()
			self.customer_code = "C" + digest[:8].upper()
			return

		self.customer_code = "C%08d" % (frappe.db.count("User Service Record") + 1)

	def fetch_from_product(self):
		"""从产品目录带出产品线，未填金额时用产品标准价兜底。"""
		if not self.product:
			return
		row = frappe.db.get_value(
			"Growth Product", self.product, ["category", "price", "billing_cycle"], as_dict=True
		)
		if not row:
			return
		if row.category:
			self.product_line = row.category
		if not self.amount and row.price:
			self.amount = flt(row.price)
		if row.billing_cycle and not self.billing_cycle:
			self.billing_cycle = row.billing_cycle

	def validate_amount(self):
		if self.amount is None:
			frappe.throw(_("请填写服务金额"))
		if flt(self.amount) < 0:
			frappe.throw(_("服务金额不能为负数"))

	def validate_dates(self):
		if self.service_start and self.service_end:
			if getdate(self.service_end) < getdate(self.service_start):
				frappe.throw(_("服务到期日不能早于服务开始日"))
		if self.service_start and self.churn_date:
			if getdate(self.churn_date) < getdate(self.service_start):
				frappe.throw(_("流失日期不能早于服务开始日"))

	def sync_status(self):
		if self.service_type == "流失":
			self.status = "已流失"
			if not self.churn_date:
				self.churn_date = nowdate()
		elif self.status in (None, "", "已流失"):
			# 非流失动作却标着"已流失"会让流失口径失真，自动纠正
			self.status = "有效"

	def validate_churn(self):
		if self.service_type == "流失":
			if not self.churn_date:
				frappe.throw(_("服务动作为「流失」时，必须填写流失日期"))
			if not self.churn_reason:
				frappe.throw(_("服务动作为「流失」时，必须选择流失原因"))

		for fieldname, label in (("winback_score", "召回可能性"), ("activity_score", "活跃度评分")):
			value = self.get(fieldname)
			if value not in (None, "") and not (0 <= int(value) <= 100):
				frappe.throw(_("{0}需在 0 - 100 之间").format(label))

	def sync_lifetime(self):
		"""生命周期 = 结束（流失/最近活跃）日期 - 服务开始日。"""
		if not self.service_start:
			self.lifetime_days = 0
			return
		end = None
		if self.service_type == "流失" and self.churn_date:
			end = self.churn_date
		elif self.last_active_on:
			end = self.last_active_on
		else:
			end = nowdate()
		self.lifetime_days = max(date_diff(end, self.service_start), 0)

	def sync_items(self):
		"""服务明细存在时，以明细合计为准回写单据金额。"""
		total = 0.0
		for row in self.service_items:
			row.qty = flt(row.qty) or 1
			row.rate = flt(row.rate)
			row.amount = flt(row.qty) * flt(row.rate)
			total += row.amount
		if self.service_items and total > 0:
			if flt(self.amount) and abs(flt(self.amount) - total) > 0.01:
				frappe.msgprint(
					_("服务金额已按明细合计调整为 {0}").format(frappe.format_value(total, "Currency")),
					alert=True,
					indicator="blue",
				)
			self.amount = total

	# ------------------------------------------------------------------
	# 白名单动作
	# ------------------------------------------------------------------
	@frappe.whitelist()
	def mark_as_churned(self, churn_reason, churn_date=None, churn_detail=None, winback_score=None):
		"""把单据标记为流失（表单按钮 / 列表批量操作调用）。"""
		if not churn_reason:
			frappe.throw(_("请选择流失原因"))
		self.service_type = "流失"
		self.status = "已流失"
		self.churn_reason = churn_reason
		self.churn_date = churn_date or nowdate()
		if churn_detail:
			self.churn_detail = churn_detail
		if winback_score is not None:
			self.winback_score = int(winback_score)
		self.sync_lifetime()
		self.save()
		return {"name": self.name, "status": self.status, "churn_date": self.churn_date}


# ----------------------------------------------------------------------
# 模块级工具
# ----------------------------------------------------------------------
def clear_dashboard_cache():
	"""单据变动后清除大屏快照缓存，避免大屏展示陈旧数据。"""
	try:
		frappe.cache().delete_value(DASHBOARD_CACHE_KEY)
		frappe.cache().delete_keys("user_growth:dash:*")
	except Exception:  # pragma: no cover - 缓存不可用时不影响业务写入
		frappe.log_error(title="user_growth: clear dashboard cache failed")


def get_permission_query_conditions(user=None):
	"""销售只能看到自己负责的单据；经理/分析师看全量。"""
	user = user or frappe.session.user
	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return ""
	if "Sales Manager" in frappe.get_roles(user) or "Growth Analyst" in frappe.get_roles(user):
		return ""
	return "`tabUser Service Record`.sales_owner = {0}".format(frappe.db.escape(user))
