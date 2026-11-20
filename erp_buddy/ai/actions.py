"""Run or cancel a write the assistant prepared, after the user pressed a button.

This is the only place ERP Buddy writes business data. It runs as the logged-in user with
normal permission checks (`insert()` / `save()` without `ignore_permissions`), so a
confirmed action can still be refused if the user lacks the right.
"""

import frappe
from frappe import _

from erp_buddy.ai.tools.base import ToolContext, doc_url, exception_text, log_action, require_doctype

# Prefix of the note that tells the model how a confirmation card was resolved.
SYSTEM_NOTICE = "[System notice]"


def resolve_action(conversation, action_id: str, confirm: bool) -> dict:
	actions = conversation.get_pending_actions()
	action = actions.get(action_id)
	if not action:
		frappe.throw(_("The action to confirm was not found."), frappe.DoesNotExistError)
	if action.get("status") != "pending":
		return {"ok": False, "status": action.get("status"), "message": _("This action was already handled.")}

	ctx = ToolContext(conversation)
	ref = {"doctype": action["doctype"], "name": action.get("name")}

	if not confirm:
		action["status"] = "cancelled"
		message = f"The user CANCELLED the action: {action['title']}."
		log_action(ctx, f"{action['type']}_document", "Cancelled", action["data"], {"cancelled": True}, ref)
		result = {"ok": True, "status": "cancelled", "message": _("Cancelled. No data was changed.")}
	else:
		result = _execute(action)
		action["status"] = "done" if result["ok"] else "failed"
		action["result"] = result
		if result["ok"]:
			ref["name"] = result["name"]
			message = f"The user CONFIRMED. Result: {result['message']} ({result['url']})."
		else:
			message = f"The user confirmed but the action FAILED: {result['message']}"
		log_action(
			ctx,
			f"{action['type']}_document",
			"Confirmed" if result["ok"] else ("Permission Denied" if result.get("permission") else "Error"),
			action["data"],
			result,
			ref,
		)

	actions[action_id] = action
	conversation.set_pending_actions(actions)

	# Tell the model what happened, so the next turn continues from the real outcome.
	messages = conversation.get_messages()
	messages.append({"role": "user", "content": f"{SYSTEM_NOTICE} {message}", "system_note": True})
	conversation.set_messages(messages)
	conversation.save(ignore_permissions=True)

	# action already embeds result; return a new dict so the two don't reference each other.
	return {**result, "action": action}


def _execute(action: dict) -> dict:
	savepoint = "erp_buddy_action"
	frappe.db.savepoint(savepoint)
	try:
		if action["type"] == "create":
			require_doctype(action["doctype"], "create")
			doc = frappe.new_doc(action["doctype"])
			doc.update(action["data"])
			doc.insert()
			message = _("Created {0} {1} ({2})")
		elif action["type"] == "update":
			require_doctype(action["doctype"], "write")
			doc = frappe.get_doc(action["doctype"], action["name"])
			doc.check_permission("write")
			doc.update(action["data"])
			doc.save()
			message = _("Updated {0} {1} ({2})")
		else:
			return {"ok": False, "message": _("Unsupported action type.")}

		return {
			"ok": True,
			"doctype": doc.doctype,
			"name": doc.name,
			"url": doc_url(doc.doctype, doc.name),
			"message": message.format(_(doc.doctype), doc.get_title() or doc.name, doc.name),
		}
	except frappe.PermissionError as e:
		frappe.db.rollback(save_point=savepoint)
		return {"ok": False, "permission": True, "message": _("Not permitted: {0}").format(exception_text(e))}
	except Exception as e:
		frappe.db.rollback(save_point=savepoint)
		if not isinstance(e, frappe.ValidationError):
			frappe.log_error(title="ERP Buddy: confirmed action failed")
		return {"ok": False, "message": exception_text(e)}
	finally:
		frappe.local.message_log = []
		frappe.flags.error_message = None
