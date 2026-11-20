"""Tool base class, shared permission helpers and the safe executor.

Permission model: every tool runs as `frappe.session.user` — the person logged in to Desk
and typing into the chatbox. Nothing here passes `ignore_permissions=True` on business
data, so the assistant can only see and change what that user could in the Desk UI.
"""

import json
import re
import unicodedata
from typing import Any
from urllib.parse import quote

import frappe
from frappe.model import default_fields, no_value_fields, table_fields

# DocTypes the assistant never reads, even for an administrator: credentials and its own config.
READ_BLOCKED_DOCTYPES = {
	"ERP Buddy Settings",
	"OAuth Bearer Token",
	"OAuth Authorization Code",
	"OAuth Client",
	"Social Login Key",
	"User Session Display",
}

# DocTypes the assistant never writes: security, schema and code. Changing these through a
# chat is not something a demo should allow, whatever the user's role.
WRITE_BLOCKED_DOCTYPES = READ_BLOCKED_DOCTYPES | {
	"User",
	"Role",
	"Role Profile",
	"Has Role",
	"User Permission",
	"DocPerm",
	"Custom DocPerm",
	"DocType",
	"Custom Field",
	"Property Setter",
	"Customize Form",
	"Server Script",
	"Client Script",
	"System Settings",
	"Module Def",
	"Workspace",
	"Report",
	"Scheduled Job Type",
	"Email Account",
	"File",
	"ERP Buddy Conversation",
	"ERP Buddy Action Log",
}

SYSTEM_FIELDS = set(default_fields) | {"amended_from", "_user_tags", "_comments", "_assign", "_liked_by"}


class ToolError(Exception):
	"""A problem the model can act on (bad doctype, unknown field). Not logged as an error."""


class ToolContext:
	def __init__(self, conversation):
		self.conversation = conversation
		self.user = frappe.session.user
		self.new_pending_actions: list[dict] = []

	def add_pending_action(self, action: dict) -> str:
		action_id = frappe.generate_hash(length=10)
		action.update(
			{"id": action_id, "status": "pending", "created_at": str(frappe.utils.now_datetime())}
		)
		actions = self.conversation.get_pending_actions()
		actions[action_id] = action
		self.conversation.set_pending_actions(actions)
		self.new_pending_actions.append(action)
		return action_id


class BaseTool:
	name: str = ""
	label: str = ""  # shown in the chat as a step, e.g. "Reading the Customer structure"
	description: str = ""
	parameters: dict = {"type": "object", "properties": {}}

	def run(self, args: dict, ctx: ToolContext) -> dict:
		raise NotImplementedError

	def step_label(self, args: dict) -> str:
		return self.label

	def schema(self) -> dict:
		return {"name": self.name, "description": self.description, "parameters": self.parameters}


# --- helpers shared by tools -------------------------------------------------------------


def require_doctype(doctype: Any, ptype: str = "read") -> str:
	"""Validate a DocType name and the user's DocType-level permission for `ptype`."""
	if not doctype or not isinstance(doctype, str):
		raise ToolError("DocType name is missing.")
	doctype = doctype.strip()
	if not frappe.db.exists("DocType", doctype):
		raise ToolError(f"DocType '{doctype}' does not exist. Use the find_doctype tool to find the right name.")
	if doctype in READ_BLOCKED_DOCTYPES or (ptype != "read" and doctype in WRITE_BLOCKED_DOCTYPES):
		raise frappe.PermissionError(f"The assistant is not allowed to {ptype} DocType {doctype}.")
	if not frappe.has_permission(doctype, ptype):
		raise frappe.PermissionError(f"The current user has no {ptype} permission on DocType {doctype}.")
	return doctype


def doc_url(doctype: str, name: str | None = None) -> str:
	slug = doctype.lower().replace(" ", "-")
	return f"/app/{slug}/{quote(str(name), safe='')}" if name else f"/app/{slug}"


def normalize(text: str) -> str:
	"""Lowercase and strip diacritics (including the Vietnamese "d" with stroke) so accented
	queries match unaccented text."""
	text = unicodedata.normalize("NFD", str(text or "").lower()).replace("đ", "d")
	return "".join(c for c in text if unicodedata.category(c) != "Mn")


def readable_fieldnames(meta, include_tables: bool = False) -> set:
	"""Fields this user may read on this DocType (respects permlevel).

	Frappe's permitted fieldnames leave out child tables; pass include_tables to add the
	ones at a permlevel the user can read.
	"""
	names = set(meta.get_permitted_fieldnames(permission_type="read") or [])
	if include_tables:
		levels = set(meta.get_permlevel_access(permission_type="read"))
		names |= {df.fieldname for df in meta.get_table_fields() if df.permlevel in levels}
	return names | {"name", "creation", "modified", "owner", "modified_by", "docstatus"}


def jsonable(value: Any, max_text: int = 1500) -> Any:
	if isinstance(value, dict):
		return {k: jsonable(v, max_text) for k, v in value.items()}
	if isinstance(value, list | tuple):
		return [jsonable(v, max_text) for v in value]
	if isinstance(value, str) and len(value) > max_text:
		return value[:max_text] + " …[truncated]"
	if value is None or isinstance(value, bool | int | float | str):
		return value
	return str(value)


def value_fields(meta) -> list:
	"""Fields that hold data, child tables included (Frappe's no_value_fields lists them too)."""
	return [df for df in meta.fields if df.fieldtype in table_fields or df.fieldtype not in no_value_fields]


def is_safe_identifier(value: str) -> bool:
	return bool(re.fullmatch(r"[A-Za-z0-9_]+", value or ""))


def exception_text(exc: BaseException) -> str:
	"""Frappe's document-level PermissionError carries no message; the reason is in flags."""
	text = frappe.utils.strip_html(str(exc) or "").strip()
	if not text:
		text = frappe.utils.strip_html(str(frappe.flags.get("error_message") or "")).strip()
	return text or type(exc).__name__


def log_action(ctx: ToolContext, tool_name: str, status: str, args: dict, result: Any, ref=None):
	"""Audit row. Written as system so a user without access to the log can still be audited."""
	try:
		frappe.get_doc(
			{
				"doctype": "ERP Buddy Action Log",
				"user": ctx.user,
				"tool_name": tool_name,
				"status": status,
				"conversation": ctx.conversation.name if not ctx.conversation.is_new() else None,
				"reference_doctype": (ref or {}).get("doctype"),
				"reference_name": (ref or {}).get("name"),
				"arguments": json.dumps(jsonable(args, 500), ensure_ascii=False, indent=1),
				"result": json.dumps(jsonable(result, 500), ensure_ascii=False, indent=1),
			}
		).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(title="ERP Buddy: failed to write action log")


def execute_tool(tool: BaseTool, args: dict, ctx: ToolContext) -> tuple[dict, str]:
	"""Run a tool, turning every failure into a result the model can read.

	Returns (result, status). Frappe's msgprint queue is cleared afterwards so errors the
	model already sees do not also pop up as Desk dialogs.
	"""
	if not isinstance(args, dict):
		args = {}
	try:
		result = tool.run(args, ctx)
		status = "Awaiting Confirmation" if result.get("status") == "awaiting_confirmation" else "Success"
	except frappe.PermissionError as e:
		result = {
			"success": False,
			"error_type": "permission_denied",
			"error": exception_text(e),
			"guidance": "The user lacks this permission. Explain that to them; do not try another way around it.",
		}
		status = "Permission Denied"
	except (ToolError, frappe.ValidationError, frappe.DoesNotExistError) as e:
		result = {"success": False, "error_type": "invalid_request", "error": exception_text(e)}
		status = "Error"
	except Exception as e:
		frappe.log_error(title=f"ERP Buddy tool error: {tool.name}")
		result = {"success": False, "error_type": "internal_error", "error": exception_text(e)}
		status = "Error"
	finally:
		frappe.local.message_log = []
		frappe.flags.error_message = None

	log_action(ctx, tool.name, status, args, result, ref=result.get("_ref") if isinstance(result, dict) else None)
	if isinstance(result, dict):
		result.pop("_ref", None)
	return result, status
