import logging


class KonbiniAdapter(logging.LoggerAdapter):
    def process(self, msg: str, kwargs):
        return f"[Konbini] {msg}", kwargs
