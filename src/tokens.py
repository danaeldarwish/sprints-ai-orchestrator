"""Exact cl100k_base tokenization. Missing vocabulary fails explicitly."""
from functools import lru_cache


class TokenizerUnavailable(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _encoder():
    try:
        import tiktoken

        return tiktoken.get_encoding("cl100k_base")
    except Exception as exc:
        raise TokenizerUnavailable("Unable to verify exact chunk sizes: cl100k_base vocabulary unavailable") from exc


def tokenizer_name() -> str:
    """Name of the tokenizer actually in use (reported in the ingestion report)."""
    _encoder()
    return "tiktoken:cl100k_base"


def count_tokens(text: str) -> int:
    """Return the number of tokens in ``text``."""
    return len(_encoder().encode(text, disallowed_special=()))
