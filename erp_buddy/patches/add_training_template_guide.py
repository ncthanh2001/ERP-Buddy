import frappe

from erp_buddy.setup.install import seed_default_guides

TITLE = "How to teach ERP Buddy (training template)"


def execute():
	"""Add the training template guide for Guide Managers, with a test case that checks it is found."""
	seed_default_guides()
	if frappe.db.exists("ERP Buddy Guide", TITLE) and not frappe.db.exists(
		"ERP Buddy Guide Test", {"expected_guide": TITLE}
	):
		frappe.get_doc(
			{"doctype": "ERP Buddy Guide Test", "question": "tôi muốn dạy thêm cho chatbox", "expected_guide": TITLE}
		).insert(ignore_permissions=True)
