"""Live schema of a DocType, as this user sees it."""

import frappe
from frappe import _
from frappe.model import table_fields

from erp_buddy.ai.tools.base import BaseTool, ToolContext, doc_url, require_doctype, value_fields


def _describe_fields(meta, readable: set | None, limit: int = 80) -> list[dict]:
	out = []
	for df in value_fields(meta):
		if readable is not None and df.fieldname not in readable:
			continue
		if df.hidden and not df.reqd:
			continue
		item = {"fieldname": df.fieldname, "label": _(df.label or df.fieldname), "type": df.fieldtype}
		if df.reqd:
			item["required"] = True
		if df.read_only:
			item["read_only"] = True
		if df.fieldtype in ("Link", "Dynamic Link") or df.fieldtype in table_fields:
			item["options"] = df.options
		elif df.fieldtype == "Select" and df.options:
			item["options"] = [o for o in df.options.split("\n") if o][:30]
		if df.default and not str(df.default).startswith(("eval:", ":")):
			item["default"] = df.default
		if df.description:
			item["description"] = frappe.utils.strip_html(df.description)[:150]
		out.append(item)
		if len(out) >= limit:
			break
	return out


class GetDocTypeInfo(BaseTool):
	name = "get_doctype_info"
	label = "Checking the form"
	description = (
		"Get the live structure of a DocType on this site: its fields (required, type, Link target, Select "
		"options), child tables and the current user's permissions (read/create/write/submit/delete). Call this "
		"before explaining how to fill in a form, and before creating or updating data."
	)
	parameters = {
		"type": "object",
		"properties": {"doctype": {"type": "string", "description": "Exact DocType name, e.g. 'Customer'"}},
		"required": ["doctype"],
	}

	def step_label(self, args):
		return f"Checking the {args.get('doctype') or ''} form".replace("  ", " ")

	def run(self, args, ctx: ToolContext):
		doctype = require_doctype(args.get("doctype"), "read")
		meta = frappe.get_meta(doctype)
		readable = set(meta.get_permitted_fieldnames(permission_type="read") or [])

		child_tables = {}
		for df in meta.get_table_fields():
			if df.fieldname not in readable:
				continue
			child_meta = frappe.get_meta(df.options)
			child_tables[df.fieldname] = {
				"doctype": df.options,
				"required": bool(df.reqd),
				"fields": [
					f
					for f in _describe_fields(child_meta, None, limit=40)
					if f.get("required") or not f.get("read_only")
				][:25],
			}

		return {
			"success": True,
			"doctype": doctype,
			"label": _(doctype),
			"module": meta.module,
			"description": meta.description,
			"is_submittable": bool(meta.is_submittable),
			"is_single": bool(meta.issingle),
			"title_field": meta.title_field,
			"naming": meta.autoname,
			"url": doc_url(doctype),
			"new_form_url": f"{doc_url(doctype)}/new",
			"your_permissions": {
				p: bool(frappe.has_permission(doctype, p))
				for p in ("read", "create", "write", "submit", "cancel", "delete")
			},
			"fields": _describe_fields(meta, readable),
			"child_tables": child_tables,
		}
