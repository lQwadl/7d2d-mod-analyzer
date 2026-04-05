"""
User feedback and transparency logging for mod operations.

This module provides callbacks and logging for:
- Directory selection
- File/folder reading (scanning)
- Folder renaming operations
- File exports

All operations are logged to a user-visible status display and optional log file.
"""

from datetime import datetime
from pathlib import Path
from typing import Callable, Optional
import os


class OperationLogger:
    """Logs mod operations transparently to user-visible callbacks."""

    def __init__(self, print_callback: Optional[Callable[[str], None]] = None):
        """
        Initialize logger.

        Args:
            print_callback: Function to call with status messages (e.g., text.insert)
        """
        self.print_callback = print_callback or print
        self.operation_stack = []

    def log(self, message: str, level: str = "INFO") -> None:
        """Log a message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = f"[{timestamp}]"

        if level == "SCAN":
            prefix = f"[{timestamp}] 📂"
        elif level == "FILE":
            prefix = f"[{timestamp}] 📄"
        elif level == "RENAME":
            prefix = f"[{timestamp}] ✏️"
        elif level == "CONFIG":
            prefix = f"[{timestamp}] ⚙️"
        elif level == "ERROR":
            prefix = f"[{timestamp}] ❌"
        elif level == "SUCCESS":
            prefix = f"[{timestamp}] ✅"
        elif level == "INFO":
            prefix = f"[{timestamp}] ℹ️"

        full_message = f"{prefix}  {message}"
        self.print_callback(full_message)

    def log_folder_selected(self, path: str) -> None:
        """Log when user selects a folder."""
        folder_path = Path(path)
        if not folder_path.exists():
            self.log(f"ERROR: Path does not exist: {path}", "ERROR")
            return

        num_items = 0
        try:
            num_items = len([x for x in folder_path.iterdir()])
        except Exception:
            pass

        self.log(
            f"📁 Selected folder: {path}",
            "CONFIG",
        )
        self.log(f"   Contains {num_items} items (files and folders)", "INFO")

    def log_scan_started(self, mods_path: str) -> None:
        """Log start of mod scanning operation."""
        self.operation_stack.append("SCAN")
        self.log(f"Scanning mods directory: {mods_path}", "SCAN")

    def log_folder_reading(self, folder_name: str, folder_path: str) -> None:
        """Log reading of a specific mod folder."""
        self.log(f"Reading folder: {folder_name}", "FILE")

    def log_file_reading(self, file_name: str, file_path: str) -> None:
        """Log reading of a specific file."""
        relative_path = Path(file_path).name
        self.log(f"  • Analyzing: {relative_path}", "FILE")

    def log_scan_complete(self, num_mods: int) -> None:
        """Log completion of mod scanning."""
        if self.operation_stack and self.operation_stack[-1] == "SCAN":
            self.operation_stack.pop()
        self.log(f"Scan complete: Found {num_mods} mod folders", "SUCCESS")

    def log_rename_started(self, old_name: str, new_name: str) -> None:
        """Log start of folder rename operation."""
        self.operation_stack.append("RENAME")
        self.log(f"Renaming folder", "RENAME")
        self.log(f"  From: {old_name}", "RENAME")
        self.log(f"  To:   {new_name}", "RENAME")

    def log_rename_complete(self, old_path: str, new_path: str) -> None:
        """Log successful completion of rename."""
        if self.operation_stack and self.operation_stack[-1] == "RENAME":
            self.operation_stack.pop()
        self.log(f"Folder renamed successfully: {Path(new_path).name}", "SUCCESS")

    def log_rename_failed(self, error: str) -> None:
        """Log failed rename operation."""
        if self.operation_stack and self.operation_stack[-1] == "RENAME":
            self.operation_stack.pop()
        self.log(f"Rename failed: {error}", "ERROR")

    def log_export_started(self, export_type: str) -> None:
        """Log start of export operation."""
        self.operation_stack.append("EXPORT")
        self.log(f"Exporting {export_type}...", "CONFIG")

    def log_export_complete(self, file_path: str) -> None:
        """Log successful export."""
        if self.operation_stack and self.operation_stack[-1] == "EXPORT":
            self.operation_stack.pop()
        filename = Path(file_path).name
        self.log(f"Export complete: {filename}", "SUCCESS")

    def log_export_failed(self, error: str) -> None:
        """Log failed export."""
        if self.operation_stack and self.operation_stack[-1] == "EXPORT":
            self.operation_stack.pop()
        self.log(f"Export failed: {error}", "ERROR")

    def log_info(self, message: str) -> None:
        """Log informational message."""
        self.log(message, "INFO")

    def log_error(self, message: str) -> None:
        """Log error message."""
        self.log(message, "ERROR")

    def clear(self) -> None:
        """Clear operation stack."""
        self.operation_stack.clear()
