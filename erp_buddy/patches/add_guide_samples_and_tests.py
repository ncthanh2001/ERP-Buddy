import frappe

from erp_buddy.setup.install import add_default_sample_questions, seed_default_guide_tests

OLD_BUYING_KEYWORD = "đơn đặt hàng"


def execute():
	"""Starter guides get sample questions and the starter test cases.

	The starter Buying guide listed "đơn đặt hàng" as a keyword, which pulled customer orders
	into it; it is removed only where that keyword is still present.
	"""
	add_default_sample_questions()

	if frappe.db.exists("ERP Buddy Guide", "Buying process"):
		keywords = frappe.db.get_value("ERP Buddy Guide", "Buying process", "keywords") or ""
		parts = [k.strip() for k in keywords.split(",") if k.strip()]
		if OLD_BUYING_KEYWORD in parts:
			parts = ["đặt hàng nhà cung cấp" if k == OLD_BUYING_KEYWORD else k for k in parts]
			doc = frappe.get_doc("ERP Buddy Guide", "Buying process")
			doc.keywords = ", ".join(parts)
			doc.save(ignore_permissions=True)

	seed_default_guide_tests()
