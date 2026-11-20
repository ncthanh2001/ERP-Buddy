"""Questions the assistant must not answer, caught before any model call.

The assistant does not explain how it works: its architecture, model, prompts, tools or
how it searches guides. The system prompt says so too, but a model can be talked round,
so the clear cases are stopped here with a fixed reply and never reach the model.

Words that refer to the assistant are found on the original text first, because the
unaccented form is ambiguous in Vietnamese ("ban" is both "bạn" (you) and "bán" (sell);
"ai" is both "AI" and "ai" (who)). They become the token `zzself`; the rest is matched on
unaccented lowercase text so diacritics do not matter.
"""

import re

from erp_buddy.ai.tools.base import normalize

SELF = "zzself"

# Matched on the original text (case-insensitive unless noted) before removing accents.
_SELF_ACCENTED = re.compile(r"\b(?:bạn|trợ lý|trợ lí|trợ lý ảo)\b", re.IGNORECASE)
_SELF_UPPER_AI = re.compile(r"\bA\.?I\b")  # "AI", not the Vietnamese "ai" (who)
_SELF_PLAIN = re.compile(
	r"\b(?:chat ?bot|chat ?box|erp buddy|buddy|bot|tro ly|you|your|yourself|assistant)\b"
)

_STRONG = r"(?:kien truc|co che|nguyen ly hoat dong|architecture|under the hood|tech stack|cong nghe (?:gi|nao))"
_PASSIVE = (
	r"(?:duoc|was|were|is|are) (?:xay dung|thiet ke|lap trinh|tao ra|lam ra|phat trien|train|huan luyen|dao tao|"
	r"built|designed|programmed|made|trained|developed|created)"
)
_WEAK = (
	r"(?:hoat dong|van hanh|xu ly|tra loi|tim kiem|lay du lieu|lay thong tin|hieu|biet|suy nghi)"
	r" (?:nhu the nao|the nao|ra sao|bang cach nao|tu dau|o dau)"
)
# The assistant's own inputs: "chatbox xử lý câu hỏi thế nào", "tìm kiếm tài liệu ra sao".
_WEAK_OBJECT = (
	r"(?:xu ly|tim|tim kiem|lay|doc|phan tich|hieu|chon) (?:cac )?(?:cau hoi|du lieu|thong tin|tai lieu|huong dan|bai)"
	r".{0,12}(?:nhu the nao|the nao|ra sao|bang cach nao|tu dau|o dau)"
)
_VENDOR = r"(?:llm|gpt|chatgpt|claude|anthropic|openai|ollama|gemini|mo hinh|model)"
_HOW_DO = rf"how (?:do|does|did) {SELF} (?:work|think|answer|search|know|decide|learn|process)"
_MAKE_SELF = (
	rf"(?:xay dung|tao ra|lam ra|lap trinh|thiet ke|phat trien|train|huan luyen|"
	rf"built|build|made|created|developed|trained|programmed) {SELF}"
)
_MECHANISM = rf"(?:{_STRONG}|{_PASSIVE}|{_WEAK}|{_WEAK_OBJECT})"

_PATTERNS = [
	re.compile(rf"\b{SELF}\b.{{0,40}}\b{_MECHANISM}\b"),
	re.compile(rf"\b{_MECHANISM}\b.{{0,20}}\b(?:cua|of) {SELF}\b"),
	re.compile(rf"\b{_HOW_DO}\b"),
	re.compile(rf"\b{_MAKE_SELF}\b"),
	# Always about how an AI assistant is put together.
	re.compile(
		r"\b(?:system prompt|prompt|rag|embedding|embeddings|vector db|vector database|function calling|"
		r"tool calling|source code|ma nguon)\b"
	),
	# Model and vendor names only when asked what the assistant is or runs on ("bạn dùng GPT à",
	# "bạn có phải là Claude"), so a customer called Claude is still fine.
	re.compile(
		rf"\b{SELF}\b.{{0,15}}\b(?:la|dung|su dung|chay|tren|dua tren|use|uses|using|are|is|run on|runs on|based on)"
		rf" (?:mo hinh |model )?{_VENDOR}\b"
	),
	re.compile(rf"\b(?:which|what) (?:llm|model|ai model)\b"),
	# Unaccented "ban" is also "bán" (sell), so it counts as "you" only in these exact shapes.
	re.compile(
		r"\bban (?:hoat dong|van hanh|suy nghi|lay du lieu|tra loi) (?:nhu the nao|the nao|ra sao|bang cach nao|tu dau)\b"
	),
	re.compile(r"\bban duoc (?:xay dung|thiet ke|lap trinh|tao ra|train|huan luyen|dao tao)\b"),
	re.compile(rf"\b{SELF}\b.{{0,30}}\b(?:tool|tools|cong cu|function|functions|plugin)\b"),
]


def _mark_self(text: str) -> str:
	text = _SELF_ACCENTED.sub(f" {SELF} ", text)
	text = _SELF_UPPER_AI.sub(f" {SELF} ", text)
	norm = " ".join(normalize(text).split())
	return _SELF_PLAIN.sub(SELF, norm)


def is_about_the_assistant(text: str) -> bool:
	"""True when the question asks how the assistant itself is built or works."""
	marked = _mark_self(text or "")
	return any(p.search(marked) for p in _PATTERNS)


# "dạy" (teach) unaccented is "day", which is also "đây" (here); recognise it with accents.
_TEACH_ACCENTED = re.compile(r"\bdạy\b", re.IGNORECASE)
TEACH = "zzteach"
_TEACH_VERB = (
	rf"(?:train|training|huan luyen|dao tao|{TEACH}|teach|cho hoc|hoc them|nap them|"
	r"bo sung kien thuc|them kien thuc|cap nhat kien thuc|nap kien thuc|add knowledge|update knowledge)"
)
_TEACH_TARGET = rf"(?:{SELF}|kien thuc|knowledge|thong tin moi|tai lieu moi)"
# Passive or "with what" phrasing asks how the assistant was built, not how to teach it.
_TEACH_PASSIVE = rf"\b(?:duoc|was|were|is|are|been) {_TEACH_VERB}\b"


def is_training_request(text: str) -> bool:
	"""True when someone wants to teach the assistant something new ("muốn dạy thêm cho chatbox").

	These are answered with how to add knowledge (ERP Buddy Guides), so they must get past
	the architecture block even though they mention training.
	"""
	marked = _mark_self(_TEACH_ACCENTED.sub(f" {TEACH} ", text or ""))
	if re.search(_TEACH_PASSIVE, marked):
		return False
	return bool(
		re.search(rf"\b{_TEACH_VERB}\b.{{0,40}}\b{_TEACH_TARGET}\b", marked)
		or re.search(rf"\b{_TEACH_TARGET}\b.{{0,30}}\b(?:hoc|hoc them|biet them|learn|learn more)\b", marked)
	)
