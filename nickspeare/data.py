"""Download the public-domain Shakespeare corpora used by Nickspeare."""

from __future__ import annotations

import shutil
import urllib.request
import zipfile
from pathlib import Path

TINY_SHAKESPEARE_URL = (
    "https://raw.githubusercontent.com/karpathy/char-rnn/master/"
    "data/tinyshakespeare/input.txt"
)
GUTENBERG_URL = "https://www.gutenberg.org/files/100/100-0.txt"
FOLGER_BASE = "https://folgerdigitaltexts.org/download/xml"
FOLGER_COMPLETE = f"{FOLGER_BASE}/FolgerDigitalTexts_XML_Complete.zip"

FOLGER_PLAYS = {
    "1H4": "FolgerDigitalTexts_XML_1H4.zip",
    "2H4": "FolgerDigitalTexts_XML_2H4.zip",
    "H5": "FolgerDigitalTexts_XML_H5.zip",
    "Ham": "FolgerDigitalTexts_XML_Ham.zip",
    "Mac": "FolgerDigitalTexts_XML_Mac.zip",
    "Rom": "FolgerDigitalTexts_XML_Rom.zip",
}


def default_cache() -> Path:
    root = Path(__file__).resolve().parent.parent
    return root / ".cache" / "corpus"


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        return
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url, timeout=60) as resp, open(tmp, "wb") as fh:
        shutil.copyfileobj(resp, fh)
    tmp.replace(dest)


def ensure_tiny_shakespeare(cache: str | Path | None = None) -> Path:
    cache = Path(cache) if cache else default_cache()
    dest = cache / "tinyshakespeare.txt"
    _download(TINY_SHAKESPEARE_URL, dest)
    return dest


def ensure_gutenberg(cache: str | Path | None = None) -> Path:
    cache = Path(cache) if cache else default_cache()
    dest = cache / "gutenberg_shakespeare.txt"
    _download(GUTENBERG_URL, dest)
    return dest


def ensure_folger(cache: str | Path | None = None, complete: bool = True) -> Path:
    """Download the Folger complete set and return the directory of XML files."""
    cache = Path(cache) if cache else default_cache()
    if complete:
        zip_path = cache / "folger_complete.zip"
        _download(FOLGER_COMPLETE, zip_path)
        out_dir = cache / "folger"
        if not out_dir.is_dir():
            out_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(out_dir)
        return out_dir
    out_dir = cache / "folger_selected"
    out_dir.mkdir(parents=True, exist_ok=True)
    for code, name in FOLGER_PLAYS.items():
        zip_path = cache / name
        _download(f"{FOLGER_BASE}/{name}", zip_path)
        play_dir = out_dir / code
        play_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(play_dir)
    return out_dir


def ensure_all(cache: str | Path | None = None) -> dict[str, Path]:
    return {
        "tiny_shakespeare": ensure_tiny_shakespeare(cache),
        "gutenberg": ensure_gutenberg(cache),
        "folger": ensure_folger(cache),
    }