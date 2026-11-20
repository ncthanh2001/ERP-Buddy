# Copyright (c) 2026, thanhnc and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

GUIDES_CACHE_KEY = "erp_buddy_guides"


class ERPBuddyGuide(Document):
	def validate(self):
		self.keywords = ", ".join(k.strip() for k in (self.keywords or "").replace("\n", ",").split(",") if k.strip())

	def on_update(self):
		clear_guides_cache()

	def on_trash(self):
		clear_guides_cache()

	def after_rename(self, old, new, merge=False):
		clear_guides_cache()


def clear_guides_cache():
	frappe.cache.delete_value(GUIDES_CACHE_KEY)
