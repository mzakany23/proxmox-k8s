"""Protocol definition for conversation data sources."""

from typing import Protocol, runtime_checkable

from .scanner import ConversationFile


@runtime_checkable
class ConversationSource(Protocol):
    """Protocol for conversation data sources.

    This protocol allows the indexer to work with different sources
    of conversation data, such as filesystem-based scanners or
    external databases like agent-progress.
    """

    def source_type(self) -> str:
        """Return identifier for this source type.

        Examples: 'filesystem', 'agent-progress'
        """
        ...

    async def scan_all(self) -> list[ConversationFile]:
        """Scan all available conversations from this source.

        Returns:
            List of ConversationFile objects ready for indexing.
        """
        ...

    async def scan_project(self, project_name: str) -> list[ConversationFile]:
        """Scan conversations for a specific project.

        Args:
            project_name: Name of the project to scan.

        Returns:
            List of ConversationFile objects for the specified project.
        """
        ...
