"""ReplayGate — re-run evidence packs and detect verification drift."""
from .gate import replay, diff_packs, is_command_safe, certificate_hash

__version__ = "0.1.0"
__all__ = ["replay", "diff_packs", "is_command_safe", "certificate_hash"]
