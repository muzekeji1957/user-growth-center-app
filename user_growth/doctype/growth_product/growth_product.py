import frappe
from frappe.model.document import Document


class GrowthProduct(Document):
	"""服务产品/套餐目录。

	产品数据可来源于既有业务系统（内容工厂 products_catalog.json、
	电商全能助手 products_catalog.json），通过 user_growth.install 导入。
	"""

	def validate(self):
		if self.price is not None and self.price < 0:
			frappe.throw("标准售价不能为负数")
		# 产品线随分类联动，避免单据侧分类与目录不一致
		if not self.category:
			frappe.throw("请选择产品线")
