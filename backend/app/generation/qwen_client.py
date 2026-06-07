class QwenClient:
    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key

    def generate(self, prompt: str) -> str:
        return (
            "Deterministic Qwen placeholder response. "
            "Real API calls are disabled in scaffold phase."
        )

