"""Whitelisted endpoints used by the Desk chat widget.

All of them need a logged-in Desk (System) user; there is no guest access. A conversation
is only ever readable and writable by the user who started it.
"""

import frappe
from frappe import _

from erp_buddy.ai.providers import ProviderError
from erp_buddy.ai.settings import get_settings, is_configured

MAX_MESSAGE_LENGTH = 4000


def _require_desk_user():
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in."), frappe.PermissionError)
	if frappe.get_cached_value("User", frappe.session.user, "user_type") != "System User":
		frappe.throw(_("ERP Buddy is only available to Desk users."), frappe.PermissionError)


def _get_own_conversation(name: str):
	if not name or not frappe.db.exists("ERP Buddy Conversation", name):
		frappe.throw(_("Conversation not found."), frappe.DoesNotExistError)
	conv = frappe.get_doc("ERP Buddy Conversation", name)
	if conv.user != frappe.session.user:
		frappe.throw(_("Conversation not found."), frappe.DoesNotExistError)
	return conv


def _new_conversation():
	return frappe.get_doc({"doctype": "ERP Buddy Conversation", "user": frappe.session.user, "messages": "[]"})


@frappe.whitelist(methods=["GET"])
def get_status() -> dict:
	_require_desk_user()
	settings = get_settings()
	return {
		"enabled": settings.enabled,
		"configured": is_configured(settings),
		"is_admin": "System Manager" in frappe.get_roles(),
		"full_name": frappe.utils.get_fullname(frappe.session.user),
	}


@frappe.whitelist(methods=["GET"])
def list_conversations() -> list:
	_require_desk_user()
	return frappe.get_all(
		"ERP Buddy Conversation",
		filters={"user": frappe.session.user},
		fields=["name", "title", "modified"],
		order_by="modified desc",
		limit=20,
	)


@frappe.whitelist(methods=["GET"])
def get_conversation(name: str) -> dict:
	from erp_buddy.ai.agent import display_messages

	_require_desk_user()
	# The widget remembers the last conversation in localStorage; it may since have been
	# deleted. Answer "missing" quietly so the widget starts fresh without an error dialog.
	owner = frappe.db.get_value("ERP Buddy Conversation", name, "user") if name else None
	if owner != frappe.session.user:
		return {"missing": True}
	conv = frappe.get_doc("ERP Buddy Conversation", name)
	return {"name": conv.name, "title": conv.title, "messages": display_messages(conv)}


@frappe.whitelist(methods=["POST"])
def send_message(message: str, conversation: str | None = None, context: str | dict | None = None) -> dict:
	from erp_buddy.ai.agent import run_turn

	_require_desk_user()
	settings = get_settings()
	if not settings.enabled:
		frappe.throw(_("ERP Buddy is disabled."))
	if not is_configured(settings):
		frappe.throw(_("ERP Buddy has no LLM configured. An administrator needs to set up ERP Buddy Settings."))

	message = (message or "").strip()
	if not message:
		frappe.throw(_("The message is empty."))
	if len(message) > MAX_MESSAGE_LENGTH:
		frappe.throw(_("The message is too long (at most {0} characters).").format(MAX_MESSAGE_LENGTH))

	conv = _get_own_conversation(conversation) if conversation else _new_conversation()
	if conv.is_new():
		conv.insert(ignore_permissions=True)

	page_context = frappe.parse_json(context) if context else None
	if not isinstance(page_context, dict):
		page_context = None
	try:
		result = run_turn(conv, message, page_context)
	except ProviderError as e:
		return {"conversation": conv.name, "error": str(e)}

	return {"conversation": conv.name, "title": conv.title, **result}


@frappe.whitelist(methods=["POST"])
def resolve_action(conversation: str, action_id: str, confirm: str | int | bool) -> dict:
	from erp_buddy.ai.actions import resolve_action as _resolve

	_require_desk_user()
	conv = _get_own_conversation(conversation)
	return _resolve(conv, action_id, frappe.utils.sbool(confirm))


@frappe.whitelist(methods=["POST"])
def delete_conversation(name: str) -> dict:
	_require_desk_user()
	conv = _get_own_conversation(name)
	# force: keep the Action Log rows that point at it; the audit outlives the chat.
	frappe.delete_doc("ERP Buddy Conversation", conv.name, ignore_permissions=True, force=True)
	return {"ok": True}
