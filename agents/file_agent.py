"""
File Agent - Handles file and directory operations
"""

import os
import shutil
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class FileAgent:
    """
    File Agent - Manages file operations.

    Capabilities:
    - Find files by name/type
    - List directory contents
    - Delete / organize files
    - Edit text files
    - Create files
    - Get file metadata

    Limitations:
    - Cannot modify system/restricted directories (safe_mode=True by default)
    """

    RESTRICTED_PATHS = [
        "c:\\windows",
        "c:\\program files",
        "c:\\program files (x86)",
        "/system",
        "/library",
        "/etc",
        "/var",
        "/usr/bin",
        "/usr/sbin",
    ]

    FILE_CATEGORIES = {
        "Documents": [".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx", ".pptx", ".odt"],
        "Images":    [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"],
        "Videos":    [".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv"],
        "Audio":     [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"],
        "Archives":  [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
        "Code":      [".py", ".js", ".ts", ".java", ".cpp", ".c", ".html", ".css", ".json"],
    }

    def __init__(self, safe_mode: bool = True):
        self.safe_mode = safe_mode

    # ─── Safety ───────────────────────────────────────────────────────────────

    def is_safe_path(self, path: str) -> bool:
        """Return False if path is in a restricted area (when safe_mode=True)."""
        if not self.safe_mode:
            return True
        path_lower = Path(path).resolve().as_posix().lower()
        return not any(r in path_lower for r in self.RESTRICTED_PATHS)

    # ─── Find / List ──────────────────────────────────────────────────────────

    def find_files(
        self,
        directory: str = ".",
        pattern: Optional[str] = None,
        file_type: Optional[str] = None,
        recursive: bool = True,
    ) -> Dict:
        """
        Find files matching the given criteria.

        Args:
            directory: Root directory to search
            pattern:   Substring to match in filename
            file_type: Extension filter, e.g. '.pdf'
            recursive: Search subdirectories

        Returns:
            {"status": ..., "files": [...], "count": int}
        """
        try:
            print(f"[FILE] Searching in: {directory}")

            if not self.is_safe_path(directory):
                return {"error": "Access denied — restricted path"}
            if not os.path.exists(directory):
                return {"error": f"Directory not found: {directory}"}

            results: List[Dict] = []
            path_obj = Path(directory)
            glob_pat = "**/*" if recursive else "*"

            for fp in path_obj.glob(glob_pat):
                if not fp.is_file():
                    continue
                if pattern and pattern.lower() not in fp.name.lower():
                    continue
                if file_type and fp.suffix.lower() != file_type.lower():
                    continue

                stat = fp.stat()
                results.append({
                    "path":     str(fp),
                    "name":     fp.name,
                    "size":     stat.st_size,
                    "type":     fp.suffix,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })

            print(f"[FILE] Found {len(results)} files")
            return {"status": "success", "files": results, "count": len(results)}

        except Exception as e:
            print(f"[ERROR] File search failed: {str(e)}")
            return {"error": str(e)}

    def list_directory(self, directory: str = ".") -> Dict:
        """List the contents of a directory."""
        try:
            if not self.is_safe_path(directory):
                return {"error": "Access denied"}
            if not os.path.exists(directory):
                return {"error": f"Directory not found: {directory}"}

            items = []
            for item in sorted(os.listdir(directory)):
                item_path = os.path.join(directory, item)
                entry: Dict = {"name": item, "path": item_path}
                if os.path.isdir(item_path):
                    entry["type"] = "directory"
                else:
                    entry["type"] = "file"
                    entry["size"] = os.path.getsize(item_path)
                items.append(entry)

            return {
                "status":    "success",
                "directory": directory,
                "items":     items,
                "count":     len(items),
            }

        except Exception as e:
            print(f"[ERROR] Directory listing failed: {str(e)}")
            return {"error": str(e)}

    # ─── Read / Write ─────────────────────────────────────────────────────────

    def read_file(self, file_path: str) -> Dict:
        """Read a text file."""
        try:
            if not self.is_safe_path(file_path):
                return {"error": "Access denied"}
            if not os.path.exists(file_path):
                return {"error": "File not found"}

            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            return {"status": "success", "file": file_path, "content": content, "size": len(content)}

        except Exception as e:
            print(f"[ERROR] File read failed: {str(e)}")
            return {"error": str(e)}

    def write_file(self, file_path: str, content: str, overwrite: bool = False) -> Dict:
        """Create or overwrite a text file."""
        try:
            if not self.is_safe_path(file_path):
                return {"error": "Access denied"}
            if os.path.exists(file_path) and not overwrite:
                return {"status": "file_exists", "message": f"File already exists: {file_path}"}

            parent = os.path.dirname(file_path)
            if parent:
                os.makedirs(parent, exist_ok=True)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            print(f"[FILE] File written: {file_path}")
            return {"status": "success", "file": file_path, "size": len(content)}

        except Exception as e:
            print(f"[ERROR] File write failed: {str(e)}")
            return {"error": str(e)}

    # ─── Delete ───────────────────────────────────────────────────────────────

    def delete_file(self, file_path: str, confirm: bool = False) -> Dict:
        """Delete a file (requires confirm=True)."""
        if not confirm:
            return {
                "status":  "needs_confirmation",
                "message": f"Are you sure you want to delete '{file_path}'?",
                "file":    file_path,
            }
        try:
            if not self.is_safe_path(file_path):
                return {"error": "Cannot delete — restricted path"}
            if not os.path.exists(file_path):
                return {"error": "File not found"}
            if os.path.isdir(file_path):
                return {"error": "Use delete_directory() for folders"}

            os.remove(file_path)
            print(f"[FILE] Deleted: {file_path}")
            return {"status": "success", "message": f"Deleted: {file_path}"}

        except Exception as e:
            print(f"[ERROR] Delete failed: {str(e)}")
            return {"error": str(e)}

    def delete_directory(self, directory: str, confirm: bool = False) -> Dict:
        """Delete a directory and all its contents (requires confirm=True)."""
        if not confirm:
            return {
                "status":    "needs_confirmation",
                "message":   f"Delete folder '{directory}' and ALL contents?",
                "directory": directory,
            }
        try:
            if not self.is_safe_path(directory):
                return {"error": "Cannot delete — restricted path"}
            if not os.path.exists(directory):
                return {"error": "Directory not found"}

            shutil.rmtree(directory)
            print(f"[FILE] Deleted directory: {directory}")
            return {"status": "success", "message": f"Deleted: {directory}"}

        except Exception as e:
            print(f"[ERROR] Directory deletion failed: {str(e)}")
            return {"error": str(e)}

    # ─── Organize ─────────────────────────────────────────────────────────────

    def organize_directory(self, directory: str, confirm: bool = False) -> Dict:
        """
        Organize files by extension into category sub-folders.
        Requires confirm=True.
        """
        if not confirm:
            return {
                "status":    "needs_confirmation",
                "message":   f"Organize files in '{directory}' into category folders?",
                "directory": directory,
            }
        try:
            if not self.is_safe_path(directory):
                return {"error": "Access denied"}
            if not os.path.exists(directory):
                return {"error": "Directory not found"}

            moved = 0
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if not os.path.isfile(item_path):
                    continue

                ext = Path(item).suffix.lower()
                for category, exts in self.FILE_CATEGORIES.items():
                    if ext in exts:
                        dest_dir = os.path.join(directory, category)
                        os.makedirs(dest_dir, exist_ok=True)
                        shutil.move(item_path, os.path.join(dest_dir, item))
                        moved += 1
                        break

            print(f"[FILE] Organized {moved} files in {directory}")
            return {
                "status":    "success",
                "message":   f"Organized {moved} files",
                "directory": directory,
            }

        except Exception as e:
            print(f"[ERROR] Organization failed: {str(e)}")
            return {"error": str(e)}

    # ─── Metadata ─────────────────────────────────────────────────────────────

    def get_file_info(self, file_path: str) -> Dict:
        """Return detailed metadata for a file."""
        try:
            if not os.path.exists(file_path):
                return {"error": "File not found"}

            stat = os.stat(file_path)
            return {
                "status":       "success",
                "file":         file_path,
                "name":         os.path.basename(file_path),
                "size":         stat.st_size,
                "created":      datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified":     datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "is_file":      os.path.isfile(file_path),
                "is_directory": os.path.isdir(file_path),
            }

        except Exception as e:
            return {"error": str(e)}


# ─── Standalone Test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    agent = FileAgent(safe_mode=True)
    result = agent.find_files(".", file_type=".py")
    print(json.dumps(result, indent=2, default=str))
