"""Install-time setup for ERP Buddy."""

import json
import os

import frappe

SETUP_DIR = os.path.dirname(__file__)
DEFAULT_GUIDES_DIR = os.path.join(SETUP_DIR, "default_guides")
DEFAULT_TESTS_FILE = os.path.join(SETUP_DIR, "default_guide_tests.json")


def after_install():
	seed_default_guides()
	seed_default_guide_tests()


def default_guides() -> list[dict]:
	"""The bundled starter guides, parsed from `default_guides/*.md`."""
	guides = []
	if not os.path.isdir(DEFAULT_GUIDES_DIR):
		return guides
	for fname in sorted(os.listdir(DEFAULT_GUIDES_DIR)):
		if not fname.endswith(".md"):
			continue
		with open(os.path.join(DEFAULT_GUIDES_DIR, fname), encoding="utf-8") as f:
			meta, content = _split_front_matter(f.read())
		guides.append(
			{
				"title": content.splitlines()[0].lstrip("# ").strip() if content else fname[:-3],
				"module": meta.get("module"),
				"keywords": meta.get("keywords", ""),
				"questions": [q.strip() for q in meta.get("questions", "").split("|") if q.strip()],
				"roles": [r.strip() for r in meta.get("roles", "").split(",") if r.strip()],
				"content": content,
			}
		)
	return guides


def seed_default_guides():
	"""Create the bundled starter guides as ERP Buddy Guide records.

	A guide whose title already exists is left alone, so running this again (a reinstall
	or a migration patch) never overwrites what a BA has edited or deleted on purpose.
	"""
	for g in default_guides():
		if frappe.db.exists("ERP Buddy Guide", g["title"]):
			continue
		module = g["module"]
		frappe.get_doc(
			{
				"doctype": "ERP Buddy Guide",
				"title": g["title"],
				"enabled": 1,
				"module": module if module and frappe.db.exists("Module Def", module) else None,
				"keywords": g["keywords"],
				"answer_mode": "Reference",
				"sample_questions": [{"question": q} for q in g["questions"]],
				"roles": [{"role": r} for r in g["roles"] if frappe.db.exists("Role", r)],
				"content": g["content"],
			}
		).insert(ignore_permissions=True)


def add_default_sample_questions():
	"""Give existing starter guides the bundled sample questions, if they have none yet."""
	for g in default_guides():
		if not g["questions"] or not frappe.db.exists("ERP Buddy Guide", g["title"]):
			continue
		doc = frappe.get_doc("ERP Buddy Guide", g["title"])
		if doc.sample_questions:
			continue
		for q in g["questions"]:
			doc.append("sample_questions", {"question": q})
		doc.save(ignore_permissions=True)


def seed_default_guide_tests():
	"""Create the bundled test questions, only on a site that has no test cases yet."""
	if frappe.db.count("ERP Buddy Guide Test") or not os.path.exists(DEFAULT_TESTS_FILE):
		return
	with open(DEFAULT_TESTS_FILE, encoding="utf-8") as f:
		cases = json.load(f)
	for case in cases:
		if frappe.db.exists("ERP Buddy Guide", case["expected_guide"]):
			frappe.get_doc({"doctype": "ERP Buddy Guide Test", **case}).insert(ignore_permissions=True)


def _split_front_matter(text: str) -> tuple[dict, str]:
	"""Parse a leading `---` block of `key: value` lines."""
	if not text.startswith("---\n"):
		return {}, text.strip()
	end = text.find("\n---\n", 4)
	if end == -1:
		return {}, text.strip()
	meta = {}
	for line in text[4:end].splitlines():
		key, sep, value = line.partition(":")
		if sep:
			meta[key.strip()] = value.strip()
	return meta, text[end + 5 :].strip()
