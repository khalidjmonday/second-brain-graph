"""Find Markdown notes and extract their explicit Obsidian-style links."""

from dataclasses import dataclass
import logging
import os
from pathlib import Path
import re
from collections.abc import Iterable


# This matches the contents of a simple Obsidian link. Normalization below
# strips supported alias and heading suffixes before graph resolution.
WIKILINK_PATTERN = re.compile(r"\[\[([^\[\]\r\n]+)\]\]")
DEFAULT_EXCLUDED_DIRS = frozenset(
    {".git", ".obsidian", ".second_brain", ".trash", ".venv", "venv", "node_modules"}
)
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class MarkdownNote:
    """A Markdown file, its text, and explicit wikilink targets."""

    path: Path
    links: tuple[str, ...]
    content: str = ""


def parse_markdown_directory(
    root: Path,
    *,
    exclude_dirs: Iterable[str] = DEFAULT_EXCLUDED_DIRS,
) -> list[MarkdownNote]:
    """Recursively scan ``root`` and return each readable Markdown note.

    Paths are sorted before reading so graph construction and duplicate-name
    resolution are deterministic across runs. Unreadable files are reported
    and skipped so one damaged file does not prevent the rest of the graph.
    """
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Markdown directory does not exist: {root}")

    excluded = {
        name.casefold() for name in (*DEFAULT_EXCLUDED_DIRS, *exclude_dirs)
    }
    markdown_paths: list[Path] = []
    for directory, child_directories, filenames in os.walk(
        root, topdown=True, onerror=_log_walk_error
    ):
        # Pruning here avoids spending time in application metadata, package
        # caches, and vendored dependencies that happen to contain Markdown.
        child_directories[:] = sorted(
            name for name in child_directories
            if name.casefold() not in excluded
            and not (Path(directory) / name).is_symlink()
        )
        markdown_paths.extend(
            Path(directory) / filename
            for filename in filenames
            if Path(filename).suffix.casefold() == ".md"
            and not (Path(directory) / filename).is_symlink()
        )

    notes: list[MarkdownNote] = []
    for path in sorted(markdown_paths):
        try:
            content = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as error:
            LOGGER.warning("Could not read Markdown note %s: %s", path, error)
            continue

        # Strip whitespace inside the brackets and ignore empty links.
        links = tuple(
            target
            for match in WIKILINK_PATTERN.finditer(content)
            if (target := _normalize_wikilink(match.group(1)))
        )
        notes.append(MarkdownNote(path=path, links=links, content=content))

    return notes


def _normalize_wikilink(raw_target: str) -> str:
    """Remove display aliases and heading fragments from a wikilink target.

    Examples: ``[[Note#Section|friendly label]]`` resolves to ``Note`` and
    ``[[folder/Note|label]]`` resolves to the vault-relative note path.
    """
    target = raw_target.split("|", maxsplit=1)[0].split("#", maxsplit=1)[0]
    return target.strip().replace("\\", "/").strip("/")


def _log_walk_error(error: OSError) -> None:
    """Report an unreadable folder while allowing the rest of the scan."""
    LOGGER.warning("Could not scan folder %s: %s", error.filename, error)
