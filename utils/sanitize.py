def sanitize_prompt(raw: str, max_length: int = 300) -> str:
    """Strip prompt injection vectors and enforce length limit."""
    import re

    text = (raw or "").strip()
    text = text[:max_length]
    text = re.sub(r'["\'`]', "", text)
    text = re.sub(r"[\{\}]", "", text)
    text = text.replace("\n", " ").replace("\r", " ")
    return text
