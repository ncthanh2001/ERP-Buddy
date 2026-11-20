"""Read ERP Buddy Settings with code-side defaults.

A Single DocType does not reliably return its declared defaults (a `tabSingles` row that
already exists keeps whatever it had), so every value falls back here.
"""

import frappe

DEFAULT_SYSTEM_NAME = "the current ERP system"
DEFAULT_RESTRICTED_REPLY = (
	"Sorry, I can't share how I am built or how I work. I can help you with how to do a task, "
	"finding data, or creating records in the ERP system."
)

DEFAULT_BASE_URLS = {
	"Anthropic": "https://api.anthropic.com",
	"OpenAI Compatible": "https://api.openai.com/v1",
}


def get_settings() -> frappe._dict:
	doc = frappe.get_cached_doc("ERP Buddy Settings")
	provider = doc.provider or "Anthropic"

	api_key = None
	if doc.api_key:
		api_key = doc.get_password("api_key", raise_exception=False)

	return frappe._dict(
		enabled=bool(doc.enabled) if doc.enabled is not None else True,
		provider=provider,
		model=((doc.custom_model if doc.model == "Custom" else doc.model) or "").strip(),
		api_key=api_key,
		base_url=(doc.base_url or DEFAULT_BASE_URLS.get(provider, "")).rstrip("/"),
		max_tokens=doc.max_tokens or 2048,
		temperature=float(doc.temperature or 0),
		max_tool_rounds=doc.max_tool_rounds or 8,
		request_timeout=doc.request_timeout or 90,
		extra_instructions=doc.extra_instructions or "",
		system_name=(doc.get("system_name") or "").strip() or DEFAULT_SYSTEM_NAME,
		restricted_reply=(doc.get("restricted_reply") or "").strip() or DEFAULT_RESTRICTED_REPLY,
	)


def is_configured(settings: frappe._dict) -> bool:
	"""An OpenAI-compatible local server (Ollama, vLLM) may not need a key."""
	if not settings.model:
		return False
	if settings.provider == "Anthropic":
		return bool(settings.api_key)
	return bool(settings.base_url)
