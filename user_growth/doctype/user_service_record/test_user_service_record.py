# -*- coding: utf-8 -*-
"""User Service Record 单元测试。

运行：``bench --site <site> run-tests --app user_growth``
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate


class TestUserServiceRecord(FrappeTestCase):
	def setUp(self):
		if not frappe.db.exists("Growth Product", "TEST-PROD"):
			frappe.get_doc(
				{
					"doctype": "Growth Product",
					"product_code": "TEST-PROD",
					"product_name": "测试产品",
					"category": "引流课",
					"price": 99,
				}
			).insert(ignore_permissions=True)

	def _new_record(self, **kwargs):
		doc = frappe.get_doc(
			{
				"doctype": "User Service Record",
				"customer_name": kwargs.pop("customer_name", "测试客户"),
				"mobile": kwargs.pop("mobile", "13800000000"),
				"region": "包头",
				"channel": "公众号",
				"product_line": "引流课",
				"product": "TEST-PROD",
				"service_type": kwargs.pop("service_type", "新开通"),
				"amount": kwargs.pop("amount", 99),
				"service_start": kwargs.pop("service_start", nowdate()),
				**kwargs,
			}
		)
		return doc

	def test_autoname_and_customer_code(self):
		doc = self._new_record().insert(ignore_permissions=True)
		self.assertTrue(doc.name.startswith("USR-"))
		self.assertTrue(doc.customer_code.startswith("C"))
		self.assertEqual(doc.status, "有效")

	def test_churn_requires_reason(self):
		doc = self._new_record(service_type="流失")
		doc.churn_reason = None
		self.assertRaises(frappe.ValidationError, doc.insert, ignore_permissions=True)

	def test_churn_sets_status_and_lifetime(self):
		start = add_days(nowdate(), -30)
		doc = self._new_record(service_type="流失", service_start=start)
		doc.churn_reason = "价格偏高"
		doc.churn_date = nowdate()
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.status, "已流失")
		self.assertGreaterEqual(doc.lifetime_days, 29)

	def test_end_before_start_rejected(self):
		doc = self._new_record()
		doc.service_end = add_days(doc.service_start, -1)
		self.assertRaises(frappe.ValidationError, doc.insert, ignore_permissions=True)

	def test_item_total_overrides_amount(self):
		doc = self._new_record(amount=1)
		doc.append("service_items", {"item_name": "课程", "qty": 2, "rate": 50})
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.amount, 100)

	def test_negative_amount_rejected(self):
		doc = self._new_record(amount=-5)
		self.assertRaises(frappe.ValidationError, doc.insert, ignore_permissions=True)
