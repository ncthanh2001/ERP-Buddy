# Copyright (c) 2026, thanhnc and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ERPBuddySettings(Document):
	def validate(self):
		if self.model == "Custom":
			self.custom_model = (self.custom_model or "").strip()
			if not self.custom_model:
				frappe.throw(_("Enter the Custom Model name."))
		else:
			self.custom_model = None
