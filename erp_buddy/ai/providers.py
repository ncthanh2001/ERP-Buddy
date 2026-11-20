"""LLM providers behind one interface.

Conversation history is stored in a provider-neutral shape and converted per call:

    {"role": "user", "content": "..."}
    {"role": "assistant", "content": "...", "tool_calls": [{"id", "name", "arguments": {...}}]}
    {"role": "tool", "tool_call_id": "...", "name": "...", "content": "<json string>"}

Both providers are called over plain HTTP with `requests`, so the app needs no SDK.
"""

import json
from dataclasses import dataclass, field

import requests


class ProviderError(Exception):
	pass


@dataclass
class LLMResponse:
	text: str = ""
	tool_calls: list = field(default_factory=list)
	stop_reason: str | None = None
	usage: dict = field(default_factory=dict)


class BaseProvider:
	def __init__(self, settings):
		self.settings = settings

	def chat(self, system: str, messages: list, tools: list) -> LLMResponse:
		raise NotImplementedError

	def _post(self, url: str, headers: dict, body: dict) -> dict:
		try:
			resp = requests.post(url, headers=headers, json=body, timeout=self.settings.request_timeout)
		except requests.Timeout:
			raise ProviderError("The LLM did not respond in time. Please try again.")
		except requests.RequestException as e:
			raise ProviderError(f"Could not connect to the LLM: {type(e).__name__}")

		if resp.status_code == 400 and "temperature" in body and "temperature" in _extract_error(resp).lower():
			# Some models accept only their default temperature; retry once without it.
			return self._post(url, headers, {k: v for k, v in body.items() if k != "temperature"})

		if resp.status_code >= 400:
			raise ProviderError(f"The LLM returned HTTP {resp.status_code}: {_extract_error(resp)}")

		try:
			return resp.json()
		except ValueError:
			raise ProviderError("The LLM returned a response that is not JSON.")


def _extract_error(resp) -> str:
	try:
		data = resp.json()
	except ValueError:
		return resp.text[:300]
	err = data.get("error") if isinstance(data, dict) else None
	if isinstance(err, dict):
		return str(err.get("message") or err)[:300]
	return str(err or data)[:300]


class AnthropicProvider(BaseProvider):
	def chat(self, system, messages, tools):
		body = {
			"model": self.settings.model,
			"max_tokens": self.settings.max_tokens,
			"temperature": self.settings.temperature,
			"system": system,
			"messages": self._convert(messages),
		}
		if tools:
			body["tools"] = [
				{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]}
				for t in tools
			]

		data = self._post(
			f"{self.settings.base_url}/v1/messages",
			{
				"x-api-key": self.settings.api_key or "",
				"anthropic-version": "2023-06-01",
				"content-type": "application/json",
			},
			body,
		)

		result = LLMResponse(stop_reason=data.get("stop_reason"), usage=data.get("usage") or {})
		texts = []
		for block in data.get("content") or []:
			if block.get("type") == "text":
				texts.append(block.get("text") or "")
			elif block.get("type") == "tool_use":
				result.tool_calls.append(
					{"id": block["id"], "name": block["name"], "arguments": block.get("input") or {}}
				)
		result.text = "\n".join(t for t in texts if t).strip()
		return result

	@staticmethod
	def _convert(messages):
		out = []

		def push(role, blocks):
			# Anthropic wants alternating roles; merge consecutive same-role turns.
			if out and out[-1]["role"] == role:
				out[-1]["content"].extend(blocks)
			else:
				out.append({"role": role, "content": list(blocks)})

		for m in messages:
			if m["role"] == "user":
				push("user", [{"type": "text", "text": m.get("content") or ""}])
			elif m["role"] == "assistant":
				blocks = []
				if m.get("content"):
					blocks.append({"type": "text", "text": m["content"]})
				for call in m.get("tool_calls") or []:
					blocks.append(
						{"type": "tool_use", "id": call["id"], "name": call["name"], "input": call["arguments"]}
					)
				if blocks:
					push("assistant", blocks)
			elif m["role"] == "tool":
				push(
					"user",
					[{"type": "tool_result", "tool_use_id": m["tool_call_id"], "content": m.get("content") or ""}],
				)
		return out


class OpenAICompatibleProvider(BaseProvider):
	def chat(self, system, messages, tools):
		body = {
			"model": self.settings.model,
			"max_tokens": self.settings.max_tokens,
			"temperature": self.settings.temperature,
			"messages": [{"role": "system", "content": system}, *self._convert(messages)],
		}
		if tools:
			body["tools"] = [
				{
					"type": "function",
					"function": {
						"name": t["name"],
						"description": t["description"],
						"parameters": t["parameters"],
					},
				}
				for t in tools
			]

		headers = {"Content-Type": "application/json"}
		if self.settings.api_key:
			headers["Authorization"] = f"Bearer {self.settings.api_key}"

		data = self._post(f"{self.settings.base_url}/chat/completions", headers, body)

		choices = data.get("choices") or []
		if not choices:
			raise ProviderError("The LLM returned no answer.")
		msg = choices[0].get("message") or {}

		result = LLMResponse(
			text=(msg.get("content") or "").strip(),
			stop_reason=choices[0].get("finish_reason"),
			usage=data.get("usage") or {},
		)
		for call in msg.get("tool_calls") or []:
			fn = call.get("function") or {}
			try:
				args = json.loads(fn.get("arguments") or "{}")
			except ValueError:
				args = {"_invalid_json": fn.get("arguments")}
			result.tool_calls.append({"id": call.get("id"), "name": fn.get("name"), "arguments": args})
		return result

	@staticmethod
	def _convert(messages):
		out = []
		for m in messages:
			if m["role"] == "user":
				out.append({"role": "user", "content": m.get("content") or ""})
			elif m["role"] == "assistant":
				item = {"role": "assistant", "content": m.get("content") or None}
				if m.get("tool_calls"):
					item["tool_calls"] = [
						{
							"id": c["id"],
							"type": "function",
							"function": {
								"name": c["name"],
								"arguments": json.dumps(c["arguments"], ensure_ascii=False),
							},
						}
						for c in m["tool_calls"]
					]
				out.append(item)
			elif m["role"] == "tool":
				out.append({"role": "tool", "tool_call_id": m["tool_call_id"], "content": m.get("content") or ""})
		return out


def get_provider(settings) -> BaseProvider:
	if settings.provider == "OpenAI Compatible":
		return OpenAICompatibleProvider(settings)
	return AnthropicProvider(settings)
