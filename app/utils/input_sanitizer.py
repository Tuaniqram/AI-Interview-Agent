import re

PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|above|prior)",
    r"forget\s+(all\s+)?(previous|above|prior)",
    r"disregard\s+(all\s+)?(previous|above|prior)",
    r"you\s+(are\s+)?(now|are\s+now)\s+",
    r"act\s+as\s+",
    r"pretend\s+(to\s+be|you\s+are)",
    r"system\s+prompt",
    r"new\s+instructions?",
    r"override\s+(instructions?|commands?)",
    r"you\s+must\s+",
    r"I\s+command\s+you",
    r"your\s+new\s+(role|persona|identity)",
    r"from\s+now\s+on",
]

def sanitize_user_input(text: str) -> str:
    if not text:
        return text
    truncated = text[:10000]
    cleaned = truncated.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"```[\s\S]*?```", "[CODE BLOCK REMOVED]", cleaned)
    return cleaned

def detect_prompt_injection(text: str) -> list[str]:
    matches = []
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            matches.append(pattern)
    return matches
