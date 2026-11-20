# Copyright (c) 2026, thanhnc and contributors
# For license information, please see license.txt

import json

from frappe.model.document import Document


class ERPBuddyConversation(Document):
	def get_messages(self) -> list:
		return json.loads(self.messages or "[]")

	def set_messages(self, messages: list) -> None:
		self.messages = json.dumps(messages, ensure_ascii=False, default=str)

	def get_pending_actions(self) -> dict:
		return json.loads(self.pending_actions or "{}")

	def set_pending_actions(self, actions: dict) -> None:
		self.pending_actions = json.dumps(actions, ensure_ascii=False, default=str)
