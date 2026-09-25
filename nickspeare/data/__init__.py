"""Packaged data and public corpus-download entry points."""
from ..downloader import ensure_all, ensure_folger, ensure_gutenberg, ensure_tiny_shakespeare

__all__ = ["ensure_all", "ensure_folger", "ensure_gutenberg", "ensure_tiny_shakespeare"]
