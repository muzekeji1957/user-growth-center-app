import frappe
from frappe.model.document import Document


class UserServiceItem(Document):
	"""服务明细子表：单据里每一项具体交付内容（课程 / 工具 / 服务…）。"""

	def validate(self):
		self.qty = self.qty or 1
		self.rate = self.rate or 0
		self.amount = (self.qty or 0) * (self.rate or 0)
