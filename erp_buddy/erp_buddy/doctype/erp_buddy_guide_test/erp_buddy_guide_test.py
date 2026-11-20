# Copyright (c) 2026, thanhnc and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class ERPBuddyGuideTest(Document):
	pass


@frappe.whitelist(methods=["POST"])
def run_all_tests() -> dict:
	"""Run every test case through the assistant's guide matcher and store each result.

	Guides are matched regardless of their role restrictions: the test checks that the
	right guide wins, not who may see it.
	"""
	frappe.has_permission("ERP Buddy Guide Test", "write", throw=True)

	from erp_buddy.ai.guides import is_confident, load_guides, match, verbatim_match

	guides = load_guides()
	cases = frappe.get_list("ERP Buddy Guide Test", fields=["name", "question", "expected_guide"], limit=0)
	failed = []
	now = now_datetime()
	for case in cases:
		results = match(case.question, guides)
		top = results[0] if results else None
		actual = top["guide"]["name"] if top else None
		passed = actual == case.expected_guide and is_confident(results)
		if not passed:
			failed.append({"question": case.question, "expected": case.expected_guide, "matched": actual})
		frappe.db.set_value(
			"ERP Buddy Guide Test",
			case.name,
			{
				"status": "Passed" if passed else "Failed",
				"actual_guide": actual,
				"similarity": top["similarity"] if top else 0,
				"answered_verbatim": 1 if verbatim_match(case.question, guides) else 0,
				"last_run": now,
			},
			update_modified=False,
		)
	return {"total": len(cases), "passed": len(cases) - len(failed), "failed": failed}
