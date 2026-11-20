"""Read and write documents, always as the current user.

Reads go through `frappe.get_list` / `doc.check_permission`, which apply role permissions,
User Permissions and permlevels. Writes never happen inside the chat turn: create and
update only *prepare* an action, and the user confirms it with a button. The confirmed
action runs `doc.insert()` / `doc.save()` without `ignore_permissions` — see actions.py.
"""

import re

import frappe
from frappe import _
from frappe.model import table_fields

from erp_buddy.ai.tools.base import (
	SYSTEM_FIELDS,
	BaseTool,
	ToolContext,
	ToolError,
	doc_url,
	is_safe_identifier,
	jsonable,
	readable_fieldnames,
	require_doctype,
	value_fields,
)

MAX_LIST = 100


def _parse_filters(filters, allowed: set):
	"""Accept {"field": value} / {"field": [op, value]} or [[field, op, value], ...]."""
	if not filters:
		return None
	if isinstance(filters, str):
		filters = frappe.parse_json(filters)

	fieldnames = []
	if isinstance(filters, dict):
		fieldnames = list(filters)
	elif isinstance(filters, list):
		for f in filters:
			if not isinstance(f, list | tuple) or len(f) < 3:
				raise ToolError("Each filter must look like [fieldname, operator, value].")
			fieldnames.append(f[1] if len(f) == 4 else f[0])
	else:
		raise ToolError("filters must be an object or an array.")

	bad = [f for f in fieldnames if f not in allowed]
	if bad:
		raise ToolError(f"Cannot filter on fields {bad} (they do not exist or you cannot read them).")
	return filters


class ListDocuments(BaseTool):
	name = "list_documents"
	label = "Looking up records"
	description = (
		"List records of a DocType that the user is allowed to see (permissions applied). Use it to look data up "
		"and to find valid values for Link fields before creating a document (e.g. a Customer, Item, Customer Group). "
		"Example filters: {\"customer_group\": \"Commercial\"} or [[\"grand_total\", \">\", 1000]]."
	)
	parameters = {
		"type": "object",
		"properties": {
			"doctype": {"type": "string"},
			"filters": {"description": "Filter conditions, as an object or an array"},
			"fields": {"type": "array", "items": {"type": "string"}, "description": "Fields to return"},
			"search": {"type": "string", "description": "Fuzzy match on name / title"},
			"order_by": {"type": "string", "description": "e.g. 'modified desc'"},
			"limit": {"type": "integer", "description": "Default 20, at most 100"},
		},
		"required": ["doctype"],
	}

	def step_label(self, args):
		return f"Looking up {args.get('doctype') or 'records'}"

	def run(self, args, ctx: ToolContext):
		doctype = require_doctype(args.get("doctype"), "read")
		meta = frappe.get_meta(doctype)
		allowed = readable_fieldnames(meta)

		requested = args.get("fields") or []
		if requested:
			fields = [f for f in requested if f in allowed and is_safe_identifier(f)]
			ignored = [f for f in requested if f not in fields]
		else:
			fields = [df.fieldname for df in meta.fields if df.in_list_view and df.fieldname in allowed][:6]
			ignored = []
		for extra in ("name", meta.title_field, "status" if meta.has_field("status") else None):
			if extra and extra in allowed and extra not in fields:
				fields.insert(0, extra) if extra == "name" else fields.append(extra)

		filters = _parse_filters(args.get("filters"), allowed)
		or_filters = None
		if args.get("search"):
			term = f"%{args['search']}%"
			or_filters = [["name", "like", term]]
			for f in {meta.title_field, meta.search_fields and meta.search_fields.split(",")[0].strip()}:
				if f and f in allowed and f != "name":
					or_filters.append([f, "like", term])

		order_by = (args.get("order_by") or "modified desc").strip()
		m = re.fullmatch(r"([a-z0-9_]+)(\s+(asc|desc))?", order_by, flags=re.I)
		if not m or m.group(1) not in allowed:
			order_by = "modified desc"

		limit = min(max(int(args.get("limit") or 20), 1), MAX_LIST)
		rows = frappe.get_list(
			doctype,
			fields=fields,
			filters=filters,
			or_filters=or_filters,
			order_by=order_by,
			limit_page_length=limit + 1,
		)
		has_more = len(rows) > limit
		rows = rows[:limit]
		for r in rows:
			r["url"] = doc_url(doctype, r.get("name"))

		result = {"success": True, "doctype": doctype, "count": len(rows), "has_more": has_more, "data": jsonable(rows, 300)}
		if ignored:
			result["ignored_fields"] = ignored
		return result


class CountDocuments(BaseTool):
	name = "count_documents"
	label = "Counting records"
	description = "Count the records of a DocType that the user can see, optionally with filters."
	parameters = {
		"type": "object",
		"properties": {"doctype": {"type": "string"}, "filters": {"description": "Filter conditions, as an object or an array"}},
		"required": ["doctype"],
	}

	def run(self, args, ctx: ToolContext):
		doctype = require_doctype(args.get("doctype"), "read")
		filters = _parse_filters(args.get("filters"), readable_fieldnames(frappe.get_meta(doctype)))
		cap = 10000
		names = frappe.get_list(doctype, filters=filters, pluck="name", limit_page_length=cap + 1)
		count = len(names)
		return {"success": True, "doctype": doctype, "count": min(count, cap), "more_than": cap if count > cap else None}


class GetDocument(BaseTool):
	name = "get_document"
	label = "Reading a document"
	description = "Read one record in full (including child tables) if the user is allowed to see it."
	parameters = {
		"type": "object",
		"properties": {"doctype": {"type": "string"}, "name": {"type": "string"}},
		"required": ["doctype", "name"],
	}

	def step_label(self, args):
		return f"Reading {args.get('doctype') or ''} {args.get('name') or ''}".strip()

	def run(self, args, ctx: ToolContext):
		doctype = require_doctype(args.get("doctype"), "read")
		name = args.get("name")
		if not name or not frappe.db.exists(doctype, name):
			raise ToolError(f"{doctype} '{name}' not found. Use list_documents to find it.")

		doc = frappe.get_doc(doctype, name)
		doc.check_permission("read")
		doc.apply_fieldlevel_read_permissions()
		data = _clean_doc_dict(doc)
		return {
			"success": True,
			"doctype": doctype,
			"name": doc.name,
			"url": doc_url(doctype, doc.name),
			"docstatus": {0: "Draft", 1: "Submitted", 2: "Cancelled"}.get(doc.docstatus),
			"data": jsonable(data),
		}


def _clean_doc_dict(doc) -> dict:
	meta = doc.meta
	password_fields = {df.fieldname for df in meta.fields if df.fieldtype == "Password"}
	out = {}
	for key, value in doc.as_dict(no_default_fields=True).items():
		if key in password_fields or key.startswith("_") or value in (None, "", []):
			continue
		df = meta.get_field(key)
		if df and df.fieldtype in table_fields:
			child_meta = frappe.get_meta(df.options)
			child_pw = {f.fieldname for f in child_meta.fields if f.fieldtype == "Password"}
			value = [
				{
					k: v
					for k, v in row.items()
					if k not in SYSTEM_FIELDS and k not in child_pw and not k.startswith("_") and v not in (None, "")
				}
				| {"idx": row.get("idx")}
				for row in value[:50]
			]
		out[key] = value
	for key in ("owner", "creation", "modified"):
		out[key] = doc.get(key)
	return out


# --- writes: prepare only, the user confirms -------------------------------------------


def _writable_fields(meta, doc=None) -> dict:
	"""fieldname -> docfield the user may set (permlevel write access, not read-only)."""
	if doc is not None:
		levels = set(doc.get_permlevel_access("write"))
	else:
		levels = set(frappe.new_doc(meta.name).get_permlevel_access("write"))
	return {
		df.fieldname: df
		for df in value_fields(meta)
		if df.fieldname not in SYSTEM_FIELDS and not df.read_only and df.permlevel in levels
	}


def _clean_values(meta, data: dict, doc=None) -> tuple[dict, list]:
	"""Keep only fields the user may write; child rows are filtered by their own meta."""
	if not isinstance(data, dict):
		raise ToolError("data must be an object {fieldname: value}.")
	writable = _writable_fields(meta, doc)
	clean, dropped = {}, []
	for key, value in data.items():
		df = writable.get(key)
		if not df:
			dropped.append(key)
			continue
		if df.fieldtype in table_fields:
			if not isinstance(value, list):
				raise ToolError(f"Child table field '{key}' must be an array of objects.")
			child_meta = frappe.get_meta(df.options)
			child_ok = {f.fieldname for f in value_fields(child_meta) if f.fieldname not in SYSTEM_FIELDS}
			rows = []
			for row in value:
				if not isinstance(row, dict):
					raise ToolError(f"Each row of '{key}' must be an object.")
				rows.append({k: v for k, v in row.items() if k in child_ok})
				dropped += [f"{key}.{k}" for k in row if k not in child_ok]
			value = rows
		clean[key] = value
	return clean, sorted(set(dropped))


def _invalid_links(meta, values: dict) -> list[str]:
	problems = []
	for key, value in values.items():
		df = meta.get_field(key)
		if not df or not value:
			continue
		if df.fieldtype == "Link" and not frappe.db.exists(df.options, value):
			problems.append(f"{key}: {df.options} '{value}' does not exist")
		elif df.fieldtype in table_fields:
			child_meta = frappe.get_meta(df.options)
			for i, row in enumerate(value, 1):
				for ck, cv in row.items():
					cdf = child_meta.get_field(ck)
					if cdf and cdf.fieldtype == "Link" and cv and not frappe.db.exists(cdf.options, cv):
						problems.append(f"{key} row {i}.{ck}: {cdf.options} '{cv}' does not exist")
	return problems


def _preview(meta, values: dict) -> list[dict]:
	items = []
	for key, value in values.items():
		df = meta.get_field(key)
		label = _(df.label) if df and df.label else key
		if df and df.fieldtype in table_fields:
			items.append({"label": label, "value": _("{0} rows").format(len(value)), "rows": jsonable(value, 200)})
		else:
			items.append({"label": label, "value": jsonable(value, 300)})
	return items


class CreateDocument(BaseTool):
	name = "create_document"
	label = "Preparing a new document"
	description = (
		"Prepare ONE new record (as a draft) with the current user's permissions. This tool does NOT write "
		"anything: the user is shown a confirmation card and must press 'Confirm'. Before calling it, use "
		"get_doctype_info to learn the required fields, ask the user for any missing values, and use "
		"list_documents to get correct values for Link fields. Never invent data."
	)
	parameters = {
		"type": "object",
		"properties": {
			"doctype": {"type": "string"},
			"data": {
				"type": "object",
				"description": "{fieldname: value}. Child tables are arrays of objects, e.g. items: [{item_code, qty, rate}]",
			},
		},
		"required": ["doctype", "data"],
	}

	def step_label(self, args):
		return f"Preparing a new {args.get('doctype') or 'document'}"

	def run(self, args, ctx: ToolContext):
		doctype = require_doctype(args.get("doctype"), "create")
		meta = frappe.get_meta(doctype)
		if meta.istable or meta.issingle:
			raise ToolError(f"{doctype} cannot be created on its own.")

		values, dropped = _clean_values(meta, args.get("data") or {})
		doc = frappe.new_doc(doctype)
		doc.update(values)

		missing = [fieldname for fieldname, _msg in doc._get_missing_mandatory_fields()]
		bad_links = _invalid_links(meta, values)
		if missing or bad_links:
			return {
				"success": False,
				"error_type": "incomplete_data",
				"missing_required_fields": [
					{"fieldname": f, "label": _(meta.get_label(f))} for f in missing
				],
				"invalid_links": bad_links,
				"dropped_fields": dropped,
				"guidance": "Ask the user for the missing or invalid values, then call again. Nothing was created.",
			}

		action_id = ctx.add_pending_action(
			{
				"type": "create",
				"doctype": doctype,
				"data": values,
				"title": _("Create {0}").format(_(doctype)),
				"preview": _preview(meta, values),
			}
		)
		return {
			"success": True,
			"status": "awaiting_confirmation",
			"action_id": action_id,
			"dropped_fields": dropped,
			"message": "A confirmation card was shown to the user. Nothing has been created YET. Summarise briefly and remind them to press 'Confirm'.",
			"_ref": {"doctype": doctype},
		}


class UpdateDocument(BaseTool):
	name = "update_document"
	label = "Preparing an update"
	description = (
		"Prepare an update to a Draft record (docstatus 0) with the current user's permissions. Nothing is "
		"written until the user presses 'Confirm'. Only pass the fields that change."
	)
	parameters = {
		"type": "object",
		"properties": {
			"doctype": {"type": "string"},
			"name": {"type": "string"},
			"data": {"type": "object", "description": "{fieldname: new value}"},
		},
		"required": ["doctype", "name", "data"],
	}

	def step_label(self, args):
		return f"Preparing an update to {args.get('doctype') or ''} {args.get('name') or ''}".strip()

	def run(self, args, ctx: ToolContext):
		doctype = require_doctype(args.get("doctype"), "write")
		name = args.get("name")
		if not name or not frappe.db.exists(doctype, name):
			raise ToolError(f"{doctype} '{name}' not found.")

		doc = frappe.get_doc(doctype, name)
		doc.check_permission("write")
		if doc.docstatus != 0:
			raise ToolError("Only Draft documents can be edited. A submitted document must be cancelled and amended in the UI.")

		meta = doc.meta
		values, dropped = _clean_values(meta, args.get("data") or {}, doc=doc)
		if not values:
			return {"success": False, "error": "No valid fields to update.", "dropped_fields": dropped}
		bad_links = _invalid_links(meta, values)
		if bad_links:
			return {"success": False, "error_type": "incomplete_data", "invalid_links": bad_links}

		preview = []
		for key, new in values.items():
			df = meta.get_field(key)
			old = doc.get(key)
			if df and df.fieldtype in table_fields:
				old = _("{0} rows").format(len(old or []))
				new_display = _("{0} rows (replaces all)").format(len(new))
			else:
				new_display = new
			preview.append({"label": _(df.label) if df and df.label else key, "old": jsonable(old, 200), "value": jsonable(new_display, 200)})

		action_id = ctx.add_pending_action(
			{
				"type": "update",
				"doctype": doctype,
				"name": name,
				"data": values,
				"title": _("Update {0} {1}").format(_(doctype), name),
				"preview": preview,
			}
		)
		return {
			"success": True,
			"status": "awaiting_confirmation",
			"action_id": action_id,
			"dropped_fields": dropped,
			"message": "A confirmation card was shown to the user. Nothing has been updated YET. Remind them to press 'Confirm'.",
			"_ref": {"doctype": doctype, "name": name},
		}
