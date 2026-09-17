"""Model selection for the Anthropic Messages API (no credentials stored here)."""
import os

DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-6"


def get_claude_model(*, fallback=False):
    """Read deployment configuration; blank values retain the supported default."""
    primary = os.getenv("ANTHROPIC_MODEL", "").strip() or DEFAULT_CLAUDE_MODEL
    return (os.getenv("ANTHROPIC_FALLBACK_MODEL", "").strip() or primary) if fallback else primary
