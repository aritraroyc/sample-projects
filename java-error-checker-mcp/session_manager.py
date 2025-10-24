"""
Session Manager for Java Error Checker MCP Service

Manages client sessions, workspace directories, and project structure replication.
"""

import os
import shutil
import uuid
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """Represents a client session."""
    session_id: str
    workspace_path: Path
    project_name: str
    created_at: float
    last_accessed: float


class SessionManager:
    """Manages sessions and workspace directories for Java projects."""

    def __init__(self, base_workspace_dir: str = "/tmp/jdtls-workspaces"):
        """
        Initialize the session manager.

        Args:
            base_workspace_dir: Base directory for all workspace sessions
        """
        self.base_workspace_dir = Path(base_workspace_dir)
        self.sessions: Dict[str, Session] = {}
        self._ensure_base_directory()

    def _ensure_base_directory(self):
        """Ensure the base workspace directory exists."""
        self.base_workspace_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Workspace base directory: {self.base_workspace_dir}")

    def create_session(self, project_name: str = "default") -> str:
        """
        Create a new session with a unique workspace.

        Args:
            project_name: Name of the Java project

        Returns:
            Session ID
        """
        import time

        session_id = str(uuid.uuid4())
        workspace_path = self.base_workspace_dir / session_id
        workspace_path.mkdir(parents=True, exist_ok=True)

        # Create standard Java project structure
        src_main_java = workspace_path / "src" / "main" / "java"
        src_test_java = workspace_path / "src" / "test" / "java"
        src_main_java.mkdir(parents=True, exist_ok=True)
        src_test_java.mkdir(parents=True, exist_ok=True)

        session = Session(
            session_id=session_id,
            workspace_path=workspace_path,
            project_name=project_name,
            created_at=time.time(),
            last_accessed=time.time()
        )

        self.sessions[session_id] = session
        logger.info(f"Created session {session_id} for project {project_name}")

        return session_id

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get a session by ID.

        Args:
            session_id: Session ID

        Returns:
            Session object or None if not found
        """
        import time

        session = self.sessions.get(session_id)
        if session:
            session.last_accessed = time.time()
        return session

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and clean up its workspace.

        Args:
            session_id: Session ID

        Returns:
            True if deleted, False if session not found
        """
        session = self.sessions.get(session_id)
        if not session:
            return False

        # Clean up workspace directory
        try:
            if session.workspace_path.exists():
                shutil.rmtree(session.workspace_path)
                logger.info(f"Deleted workspace for session {session_id}")
        except Exception as e:
            logger.error(f"Error deleting workspace for session {session_id}: {e}")

        # Remove from sessions
        del self.sessions[session_id]
        return True

    def write_file(self, session_id: str, file_path: str, content: str) -> bool:
        """
        Write a Java file to the session workspace.

        Args:
            session_id: Session ID
            file_path: Relative file path (e.g., "com/example/Main.java")
            content: File content

        Returns:
            True if successful, False otherwise
        """
        session = self.get_session(session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            return False

        # Determine full path (default to src/main/java)
        if not file_path.startswith("src/"):
            full_path = session.workspace_path / "src" / "main" / "java" / file_path
        else:
            full_path = session.workspace_path / file_path

        # Ensure parent directories exist
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        try:
            full_path.write_text(content, encoding='utf-8')
            logger.info(f"Wrote file {file_path} to session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error writing file {file_path}: {e}")
            return False

    def read_file(self, session_id: str, file_path: str) -> Optional[str]:
        """
        Read a file from the session workspace.

        Args:
            session_id: Session ID
            file_path: Relative file path

        Returns:
            File content or None if not found
        """
        session = self.get_session(session_id)
        if not session:
            return None

        # Determine full path
        if not file_path.startswith("src/"):
            full_path = session.workspace_path / "src" / "main" / "java" / file_path
        else:
            full_path = session.workspace_path / file_path

        try:
            return full_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None

    def list_files(self, session_id: str) -> List[str]:
        """
        List all Java files in the session workspace.

        Args:
            session_id: Session ID

        Returns:
            List of relative file paths
        """
        session = self.get_session(session_id)
        if not session:
            return []

        java_files = []
        for java_file in session.workspace_path.rglob("*.java"):
            relative_path = java_file.relative_to(session.workspace_path)
            java_files.append(str(relative_path))

        return java_files

    def get_workspace_path(self, session_id: str) -> Optional[Path]:
        """
        Get the workspace path for a session.

        Args:
            session_id: Session ID

        Returns:
            Workspace path or None if session not found
        """
        session = self.get_session(session_id)
        return session.workspace_path if session else None

    def cleanup_old_sessions(self, max_age_seconds: int = 3600):
        """
        Clean up sessions older than max_age_seconds.

        Args:
            max_age_seconds: Maximum age in seconds
        """
        import time

        current_time = time.time()
        sessions_to_delete = []

        for session_id, session in self.sessions.items():
            if current_time - session.last_accessed > max_age_seconds:
                sessions_to_delete.append(session_id)

        for session_id in sessions_to_delete:
            self.delete_session(session_id)
            logger.info(f"Cleaned up old session {session_id}")
