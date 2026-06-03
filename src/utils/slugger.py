import re

def generate_slug(text: str) -> str:
    text = text.lower()
    text = text.replace(" ", "-")
    text = re.sub(r'[^a-z0-9-]', '', text)
    text = re.sub(r'-+', '-', text)
    return text.strip("-")
