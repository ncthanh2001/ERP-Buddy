"""Matching questions to ERP Buddy Guides.

One matcher serves three callers, so what the BA tests is what users get:
- the `search_guides` tool (the model asks for guides),
- the verbatim short-circuit in the agent (an approved answer, no model involved),
- the guide test runner (ERP Buddy Guide Test).

Scoring is lexical: keyword phrases, title / keyword / content words, and how close the
question is to each sample question the BA wrote. No embeddings or vector store.
"""

import re

import frappe

from erp_buddy.ai.tools.base import normalize
from erp_buddy.erp_buddy.doctype.erp_buddy_guide.erp_buddy_guide import GUIDES_CACHE_KEY

# Filler words in English and (unaccented) Vietnamese that say nothing about the topic.
STOPWORDS = {
	"how", "do", "does", "the", "a", "an", "to", "in", "of", "for", "and", "or", "is", "are", "what",
	"i", "me", "my", "we", "can", "with", "on", "please", "lam", "the", "nao", "sao", "cach", "toi",
	"minh", "cho", "va", "la", "co", "khong", "huong", "dan", "gi", "o", "de", "voi", "cua", "mot",
	"nhung", "cac", "thi", "vay", "a", "nhe", "giup", "dau", "ban", "oi", "duoc", "can", "muon",
}

# A sample question this close (word overlap) to the user's question is a confident match.
CONFIDENT_SIMILARITY = 0.6
# Verbatim answers are returned without the model, so they need a closer match: the
# question must be essentially a sample question, not a longer request that contains one.
VERBATIM_SIMILARITY = 0.75
SAMPLE_WEIGHT = 40


def words(text: str) -> list[str]:
	return [w for w in re.findall(r"\w+", normalize(text)) if len(w) > 1]


def content_words(text: str) -> set[str]:
	return {w for w in words(text) if w not in STOPWORDS}


def load_guides() -> list[dict]:
	"""All enabled guides, prepared for matching, cached until a guide changes.

	Guides are content that BAs curate for the assistant, not user data, so they are read
	without per-user DocType permission; who sees a guide is decided by its roles.
	"""
	cached = frappe.cache.get_value(GUIDES_CACHE_KEY)
	if cached is not None:
		return cached

	rows = frappe.get_all(
		"ERP Buddy Guide",
		filters={"enabled": 1},
		fields=["name", "title", "module", "keywords", "content", "answer_mode", "verbatim_answer"],
		order_by="title asc",
	)
	children: dict[str, dict[str, list]] = {}
	for child_doctype, field in (("ERP Buddy Guide Role", "role"), ("ERP Buddy Guide Question", "question")):
		for r in frappe.get_all(
			child_doctype,
			filters={"parenttype": "ERP Buddy Guide"},
			fields=["parent", field],
			order_by="idx asc",
		):
			children.setdefault(r.parent, {}).setdefault(field, []).append(r[field])

	guides = []
	for row in rows:
		extra = children.get(row.name, {})
		phrases = [normalize(k).strip() for k in (row.keywords or "").split(",") if k.strip()]
		questions = extra.get("question", [])
		guides.append(
			{
				"name": row.name,
				"title": row.title,
				"module": row.module,
				"content": row.content or "",
				"answer_mode": row.answer_mode or "Reference",
				"verbatim_answer": row.verbatim_answer or "",
				"roles": extra.get("role", []),
				"sample_questions": questions,
				"keyword_phrases": phrases,
				"title_words": set(words(row.title)),
				"keyword_words": {w for p in phrases for w in p.split() if len(w) > 1},
				"content_words": words(row.content or ""),
				"question_words": [content_words(q) for q in questions],
			}
		)
	frappe.cache.set_value(GUIDES_CACHE_KEY, guides)
	return guides


def visible_guides(user: str | None = None) -> list[dict]:
	"""Guides the user's roles may see. Guides without roles are for everyone."""
	user_roles = set(frappe.get_roles(user))
	return [g for g in load_guides() if not g["roles"] or user_roles.intersection(g["roles"])]


def _similarity(query_words: set[str], sample_words: set[str]) -> float:
	if not query_words or not sample_words:
		return 0.0
	return len(query_words & sample_words) / len(query_words | sample_words)


def match(query: str, guides: list[dict]) -> list[dict]:
	"""Score every guide against the question, best first. Guides scoring 0 are dropped."""
	query_norm = " ".join(words(query))
	padded = f" {query_norm} "
	q_all = words(query)
	q_content = content_words(query)

	results = []
	for g in guides:
		score = 0.0
		for phrase in g["keyword_phrases"]:
			if phrase and f" {phrase} " in padded:
				score += 10 * len(phrase.split())
		for w in q_all:
			if w in STOPWORDS:
				continue
			if w in g["title_words"]:
				score += 5
			if w in g["keyword_words"]:
				score += 3
			score += min(g["content_words"].count(w), 5)

		best_sim, best_question = 0.0, None
		for question, sample in zip(g["sample_questions"], g["question_words"], strict=False):
			sim = _similarity(q_content, sample)
			if sim > best_sim:
				best_sim, best_question = sim, question
		score += best_sim * SAMPLE_WEIGHT

		if score > 0:
			results.append(
				{"guide": g, "score": round(score, 1), "similarity": round(best_sim, 2), "matched_question": best_question}
			)
	results.sort(key=lambda r: -r["score"])
	return results


def is_confident(results: list[dict]) -> bool:
	"""True when the top guide is clearly the answer; otherwise the model gets the catalog."""
	if not results:
		return False
	top = results[0]
	if top["similarity"] >= CONFIDENT_SIMILARITY:
		return True
	runner_up = results[1]["score"] if len(results) > 1 else 0
	return top["score"] >= 15 and top["score"] >= 2 * runner_up


def verbatim_match(query: str, guides: list[dict]) -> dict | None:
	"""The match whose approved answer should be returned as-is, if any."""
	results = match(query, guides)
	if not results:
		return None
	top = results[0]
	guide = top["guide"]
	if guide["answer_mode"] == "Verbatim" and guide["verbatim_answer"] and top["similarity"] >= VERBATIM_SIMILARITY:
		return top
	return None


def catalog(guides: list[dict], limit: int = 60) -> list[dict]:
	"""A compact list of guides for the model to choose from when matching is unsure."""
	return [
		{"title": g["title"], "module": g["module"], "sample_questions": g["sample_questions"][:4]}
		for g in guides[:limit]
	]
