"""Tools that help the user learn the system: built-in guides and what this site offers."""

import frappe
from frappe import _

from erp_buddy.ai.tools.base import (
	READ_BLOCKED_DOCTYPES,
	BaseTool,
	ToolContext,
	doc_url,
	normalize,
)

# Framework modules most users never need to be told about in an overview.
TECHNICAL_MODULES = {
	"Core",
	"Custom",
	"Desk",
	"Email",
	"Integrations",
	"Printing",
	"Website",
	"Workflow",
	"Automation",
	"Social",
	"Geo",
	"Data Migration",
	"ERP Buddy",
	"Frappe Assistant Core",
	"Telephony",
	"Communication",
	"Bulk Transaction",
	"Portal",
	"Utilities",
	"EDI",
	"Regional",
	"ERPNext Integrations",
	"Erpnext Integrations",
}


def _guide_result(match: dict) -> dict:
	g = match["guide"]
	item = {"title": g["title"], "module": g["module"]}
	if g["answer_mode"] == "Verbatim" and g["verbatim_answer"]:
		item["approved_answer"] = g["verbatim_answer"]
		item["instruction"] = "Reply with approved_answer word for word. Do not add, drop or reorder steps."
	else:
		item["content"] = g["content"]
	return item


class SearchGuides(BaseTool):
	name = "search_guides"
	label = "Searching the user guides"
	description = (
		"Search the company's ERPNext user guides (maintained by the business team): selling, buying, stock, "
		"accounting, CRM, how to create customers, orders, invoices... Always call this before answering a "
		"'how do I...' question. Pass the user's question as they wrote it. Only guides the user's roles may "
		"see are searched. When the match is uncertain you also get a catalog of all guides: if one of them "
		"fits better, open it with get_guide."
	)
	parameters = {
		"type": "object",
		"properties": {"query": {"type": "string", "description": "The user's question, in any language"}},
		"required": ["query"],
	}

	def run(self, args, ctx: ToolContext):
		from erp_buddy.ai import guides as guide_matcher

		guides = guide_matcher.visible_guides()
		results = guide_matcher.match(args.get("query") or "", guides)
		confident = guide_matcher.is_confident(results)

		# A runner-up is only worth the tokens when it is nearly as relevant as the best match.
		top = [r for r in results[:2] if r["score"] * 2 >= results[0]["score"]] if results else []
		out = {
			"success": True,
			"confidence": "high" if confident else "low",
			"results": [_guide_result(r) for r in top],
		}
		if not confident:
			out["catalog"] = guide_matcher.catalog(guides)
			out["note"] = (
				"The match is uncertain. Compare the question with the catalog (titles and sample questions); "
				"if another guide fits, call get_guide with its title. If none fits, answer from general ERPNext "
				"knowledge and check it against this site with list_features / get_doctype_info."
			)
		return out


class GetGuide(BaseTool):
	name = "get_guide"
	label = "Opening a user guide"
	description = "Open one user guide by its exact title (from the catalog returned by search_guides)."
	parameters = {
		"type": "object",
		"properties": {"title": {"type": "string", "description": "Exact guide title"}},
		"required": ["title"],
	}

	def step_label(self, args):
		return f"Opening the guide '{args.get('title') or ''}'"

	def run(self, args, ctx: ToolContext):
		from erp_buddy.ai import guides as guide_matcher

		title = (args.get("title") or "").strip()
		for g in guide_matcher.visible_guides():
			if g["title"].lower() == title.lower():
				return {"success": True, **_guide_result({"guide": g})}
		return {"success": False, "error": f"No guide titled '{title}' is available to this user."}


class ListFeatures(BaseTool):
	name = "list_features"
	label = "Listing the features you can use"
	description = (
		"List the features (modules, DocTypes, reports) the CURRENT USER can access on this site. Omit 'module' "
		"for an overview by module; pass 'module' (e.g. 'Selling', 'Stock', 'Accounts') for that module's "
		"DocTypes and reports."
	)
	parameters = {
		"type": "object",
		"properties": {"module": {"type": "string", "description": "Module name, e.g. 'Selling'"}},
	}

	def step_label(self, args):
		return f"Listing the features of module {args['module']}" if args.get("module") else self.label

	def run(self, args, ctx: ToolContext):
		module = (args.get("module") or "").strip()
		module_app = {m.name: m.app_name for m in frappe.get_all("Module Def", fields=["name", "app_name"])}

		filters = {"istable": 0}
		if module:
			match = next((m for m in module_app if m.lower() == module.lower()), None)
			if not match:
				return {
					"success": False,
					"error": f"There is no module '{module}'.",
					"available_modules": sorted(m for m in module_app if m not in TECHNICAL_MODULES),
				}
			module = match
			filters["module"] = module

		doctypes = frappe.get_all(
			"DocType",
			filters=filters,
			fields=["name", "module", "issingle", "is_submittable", "description"],
			order_by="name asc",
		)

		readable = [
			d
			for d in doctypes
			if d.name not in READ_BLOCKED_DOCTYPES and frappe.has_permission(d.name, "read")
		]

		if not module:
			by_module: dict[str, list] = {}
			for d in readable:
				if d.module in TECHNICAL_MODULES:
					continue
				by_module.setdefault(d.module, []).append(d.name)
			return {
				"success": True,
				"user": ctx.user,
				"modules": [
					{
						"module": m,
						"app": module_app.get(m),
						"doctype_count": len(names),
						"examples": names[:8],
					}
					for m, names in sorted(by_module.items(), key=lambda x: -len(x[1]))
				],
				"hint": "Call again with the module parameter for details.",
			}

		reports = []
		for r in frappe.get_all(
			"Report",
			filters={"module": module, "disabled": 0},
			fields=["name", "report_type", "ref_doctype"],
		):
			try:
				if frappe.get_cached_doc("Report", r.name).is_permitted():
					reports.append({"name": r.name, "type": r.report_type, "url": f"/app/query-report/{r.name}"})
			except Exception:
				continue

		return {
			"success": True,
			"module": module,
			"doctypes": [
				{
					"doctype": d.name,
					"label": _(d.name),
					"single": bool(d.issingle),
					"submittable": bool(d.is_submittable),
					"can_create": bool(frappe.has_permission(d.name, "create")) and not d.issingle,
					"url": doc_url(d.name),
					"description": (d.description or "")[:150] or None,
				}
				for d in readable
			],
			"reports": reports[:40],
		}


class FindDocType(BaseTool):
	name = "find_doctype"
	label = "Finding the right screen"
	description = (
		"Find a DocType (document type or master) by name, e.g. 'customer' -> Customer, 'sales invoice' -> "
		"Sales Invoice. Prefer English keywords. Only returns DocTypes the user can read."
	)
	parameters = {
		"type": "object",
		"properties": {"query": {"type": "string", "description": "Name to look for (English works best)"}},
		"required": ["query"],
	}

	def run(self, args, ctx: ToolContext):
		query = normalize(args.get("query") or "").strip()
		if not query:
			return {"success": False, "error": "The query is empty."}
		words = query.split()

		results = []
		for d in frappe.get_all("DocType", filters={"istable": 0}, fields=["name", "module", "is_submittable"]):
			haystack = normalize(f"{d.name} {_(d.name)} {d.module}")
			if all(w in haystack for w in words):
				if d.name in READ_BLOCKED_DOCTYPES or not frappe.has_permission(d.name, "read"):
					continue
				exact = normalize(d.name) == query or normalize(_(d.name)) == query
				results.append((0 if exact else len(d.name), d))
		results.sort(key=lambda x: x[0])

		return {
			"success": True,
			"results": [
				{
					"doctype": d.name,
					"label": _(d.name),
					"module": d.module,
					"submittable": bool(d.is_submittable),
					"can_create": bool(frappe.has_permission(d.name, "create")),
				}
				for _score, d in results[:10]
			],
			"note": None if results else "Nothing found. Try English keywords (e.g. 'Invoice', 'Item').",
		}
