import hashlib

import frappe

from erp_buddy.setup.install import default_guides

OLD_TITLE = "ERPNext overview and main modules"
NEW_TITLE = "ERP system overview and main modules"
# sha1 of the bundled overview content before it stopped naming ERPNext and DocTypes.
ORIGINAL_CONTENT_SHA1 = "8e06ae39301d338b76de432cdf675adae73d5749"


def execute():
	"""Rename the starter overview guide and drop product and DocType wording from it.

	Only a guide still holding the original bundled text is changed; one a BA edited is left
	as it is (the assistant's naming rule still keeps product names out of its replies).
	"""
	if not frappe.db.exists("ERP Buddy Guide", OLD_TITLE) or frappe.db.exists("ERP Buddy Guide", NEW_TITLE):
		return
	content = frappe.db.get_value("ERP Buddy Guide", OLD_TITLE, "content") or ""
	if hashlib.sha1(content.strip().encode()).hexdigest() != ORIGINAL_CONTENT_SHA1:
		return

	bundled = next((g for g in default_guides() if g["title"] == NEW_TITLE), None)
	if not bundled:
		return
	frappe.rename_doc("ERP Buddy Guide", OLD_TITLE, NEW_TITLE, force=True)
	doc = frappe.get_doc("ERP Buddy Guide", NEW_TITLE)
	doc.title = NEW_TITLE
	doc.content = bundled["content"]
	existing = {row.question for row in doc.sample_questions}
	for q in bundled["questions"]:
		if q not in existing:
			doc.append("sample_questions", {"question": q})
	doc.save(ignore_permissions=True)
