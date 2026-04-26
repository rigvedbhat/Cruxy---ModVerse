import re
import unicodedata


def sanitize_prompt(raw: str, max_length: int = 300) -> str:
    text = (raw or "").strip()
    # Normalize unicode - converts fullwidth chars, lookalikes, and compatibility forms.
    text = unicodedata.normalize("NFKC", text)
    text = text[:max_length]
    text = re.sub(r'["\'`\u201c\u201d\u2018\u2019]', "", text)
    text = re.sub(r"[\{\}\[\]]", "", text)
    text = re.sub(r"[\u200b-\u200f\u202a-\u202e\ufeff]", "", text)
    text = text.replace("\n", " ").replace("\r", " ")
    return text.strip()
