import re

def clean_text(s: str) -> str:
    if not s:
        return ""
    s = s.replace('\u200b',' ').replace('\xa0',' ')
    s = re.sub(r'\s+', ' ', s).strip()
    return s
