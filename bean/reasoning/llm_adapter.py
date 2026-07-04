"""Provider adapter interfaces for Brain 0.11."""

class LLMAdapterBase:
    adapter_name = "base"
    model_name = "unknown"
    def complete(self, prompt: str, context: dict | None = None) -> dict:
        raise NotImplementedError


class AdapterError(RuntimeError):
    pass
