import re

BLOCKED_PATTERNS = [
    r"\b(ignore|disregard)\s+(previous|all)\s+instructions\b",
    r"\bsystem\s+prompt\b",
    r"\bjailbreak\b",
]
TOXIC_WORDS: set[str] = set()   # populate from a real list / library


def validate_input(text: str) -> tuple[bool, str]:
    lowered = text.lower()
    for pat in BLOCKED_PATTERNS:
        if re.search(pat, lowered):
            return False, "Prompt-injection attempt blocked."
    if any(w in lowered for w in TOXIC_WORDS):
        return False, "Input violates content policy."
    if len(text) > 4000:
        return False, "Input too long (max 4000 chars)."
    return True, ""


def validate_output(text: str) -> str:
    for w in TOXIC_WORDS:
        text = text.replace(w, "[redacted]")
    return text
