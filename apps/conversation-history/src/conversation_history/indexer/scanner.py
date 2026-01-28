"""Scanner for discovering conversation files."""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ConversationFile:
    """Represents a discovered conversation file."""

    file_path: str
    project_name: str
    feature_name: str | None
    doc_type: str  # checkpoint, instructions, docs, other
    title: str | None
    content: str
    content_hash: str


class ConversationScanner:
    """Scans for conversation files in project directories.

    Implements the ConversationSource protocol for filesystem-based
    conversation discovery.
    """

    def __init__(self, projects_root: str = "/Users/michaelzakany/projects"):
        self.projects_root = Path(projects_root)

    def source_type(self) -> str:
        """Return identifier for this source type."""
        return "filesystem"

    async def scan_all(self) -> list[ConversationFile]:
        """Scan all projects for conversation files."""
        files = []
        for project_dir in self.projects_root.iterdir():
            if project_dir.is_dir() and not project_dir.name.startswith("."):
                files.extend(await self.scan_project(project_dir.name))
        return files

    async def scan_project(self, project_name: str) -> list[ConversationFile]:
        """Scan a single project for conversation files."""
        project_dir = self.projects_root / project_name
        conversation_dir = project_dir / "conversation"

        if not conversation_dir.exists():
            return []

        files = []
        for file_path in conversation_dir.rglob("*.md"):
            try:
                conv_file = self._parse_file(file_path, project_name)
                if conv_file:
                    files.append(conv_file)
            except Exception as e:
                print(f"Error parsing {file_path}: {e}")
                continue

        return files

    def _parse_file(self, file_path: Path, project_name: str) -> ConversationFile | None:
        """Parse a conversation file and extract metadata."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Try with latin-1 as fallback
            content = file_path.read_text(encoding="latin-1")

        # Remove null bytes that PostgreSQL doesn't accept
        content = content.replace("\x00", "")

        if not content.strip():
            return None

        # Calculate content hash for change detection
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        # Determine doc_type and feature_name from path
        relative_path = file_path.relative_to(
            self.projects_root / project_name / "conversation"
        )
        parts = list(relative_path.parts)

        doc_type = self._determine_doc_type(file_path.name, parts)
        feature_name = self._extract_feature_name(parts)
        title = self._extract_title(content, file_path.name)

        return ConversationFile(
            file_path=str(file_path),
            project_name=project_name,
            feature_name=feature_name,
            doc_type=doc_type,
            title=title,
            content=content,
            content_hash=content_hash,
        )

    def _determine_doc_type(self, filename: str, path_parts: list[str]) -> str:
        """Determine document type from filename and path."""
        filename_lower = filename.lower()

        if "checkpoint" in filename_lower:
            return "checkpoint"
        if "instruction" in filename_lower or filename_lower == "instructions.md":
            return "instructions"
        if "readme" in filename_lower:
            return "docs"

        # Check path parts for doc type hints
        for part in path_parts:
            part_lower = part.lower()
            if "checkpoint" in part_lower:
                return "checkpoint"
            if "instruction" in part_lower:
                return "instructions"
            if "doc" in part_lower:
                return "docs"

        return "other"

    def _extract_feature_name(self, path_parts: list[str]) -> str | None:
        """Extract feature name from path."""
        # Look for feature directory in path
        for part in path_parts[:-1]:  # Exclude filename
            # Skip common non-feature directories
            if part.lower() in ("common", "docs", "checkpoints", "instructions"):
                continue
            return part
        return None

    def _extract_title(self, content: str, filename: str) -> str | None:
        """Extract title from content or filename."""
        # Try to find first markdown heading
        lines = content.split("\n")
        for line in lines[:10]:  # Check first 10 lines
            if line.startswith("# "):
                return line[2:].strip()

        # Fall back to filename without extension
        return Path(filename).stem.replace("-", " ").replace("_", " ").title()


def chunk_content(
    content: str, chunk_size: int = 3000, overlap: int = 500
) -> list[str]:
    """Split content into overlapping chunks for better embedding."""
    if len(content) <= chunk_size:
        return [content]

    chunks = []
    start = 0

    while start < len(content):
        end = start + chunk_size

        # Try to break at paragraph boundary
        if end < len(content):
            # Look for paragraph break within last 20% of chunk
            search_start = end - int(chunk_size * 0.2)
            paragraph_break = content.rfind("\n\n", search_start, end)
            if paragraph_break > start:
                end = paragraph_break

        chunks.append(content[start:end].strip())
        prev_start = start
        start = end - overlap

        # Ensure we make progress
        if start <= prev_start:
            start = end

    return [c for c in chunks if c]  # Remove empty chunks
