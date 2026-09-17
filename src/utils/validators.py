import re

class Validators:
    @staticmethod
    def is_email(text):
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, text))

    @staticmethod
    def is_phone(text):
        # Matches formats like 05xx xxx xx xx or +90 ...
        pattern = r'^(\+90|0)?5[0-9]{9}$'
        # Clean text from spaces/parens first
        clean_text = re.sub(r'[\s\(\)\-]', '', text)
        return bool(re.match(pattern, clean_text))

    @staticmethod
    def is_not_empty(text):
        return len(text.strip()) > 0

    @staticmethod
    def parse_numeric(text, default=None):
        raw = str(text or "").strip().replace(" ", "")
        if not raw:
            return default

        normalized = raw
        if "," in normalized and "." in normalized:
            if normalized.rfind(",") > normalized.rfind("."):
                normalized = normalized.replace(".", "").replace(",", ".")
            else:
                normalized = normalized.replace(",", "")
        elif "," in normalized:
            normalized = normalized.replace(".", "").replace(",", ".")

        try:
            return float(normalized)
        except ValueError:
            return default

    @staticmethod
    def is_numeric(text):
        return Validators.parse_numeric(text, default=None) is not None
