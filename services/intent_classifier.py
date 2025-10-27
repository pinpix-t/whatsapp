"""
Lightweight intent classifier for WhatsApp CSR bot.
Uses keyword/regex heuristics first; can be extended with LLM fallback.
"""

import re
from typing import Literal, Optional

Intent = Literal[
	"smalltalk",
	"order_tracking",
	"returns",
	"product",
	"billing",
	"complaint",
	"help",
	"unknown",
]


SMALLTALK = re.compile(r"\b(hi|hello|hey|hola|howdy|good\s*(morning|afternoon|evening))\b", re.I)
TRACKING = re.compile(r"\b(track|tracking|where\s*is\s*my\s*order|order\s*status|delivery|shipping)\b", re.I)
RETURNS = re.compile(r"\b(return|refund|exchange|replace|replacement)\b", re.I)
PRODUCT = re.compile(r"\b(product|size|color|availability|stock|price|discount|coupon|promo)\b", re.I)
BILLING = re.compile(r"\b(bill|billing|invoice|charge|charged|payment|card|credit|debit)\b", re.I)
COMPLAINT = re.compile(r"\b(complain|complaint|angry|bad|terrible|late|delay|damaged|broken)\b", re.I)
HELP = re.compile(r"\b(help|support|agent|human)\b", re.I)


def classify_intent(text: str) -> Intent:
	if not text:
		return "unknown"
	t = text.strip().lower()
	if SMALLTALK.search(t):
		return "smalltalk"
	if TRACKING.search(t):
		return "order_tracking"
	if RETURNS.search(t):
		return "returns"
	if PRODUCT.search(t):
		return "product"
	if BILLING.search(t):
		return "billing"
	if COMPLAINT.search(t):
		return "complaint"
	if HELP.search(t):
		return "help"
	return "unknown"


def is_command(text: str) -> Optional[str]:
	"""Recognize quick commands like 'more', 'notify me', 'stop', 'help'."""
	if not text:
		return None
	t = text.strip().lower()
	if t in {"more", "+more"}:
		return "more"
	if t in {"notify", "notify me"}:
		return "notify"
	if t in {"stop", "unsubscribe", "opt out"}:
		return "stop"
	if t in {"help", "menu"}:
		return "help"
	return None
