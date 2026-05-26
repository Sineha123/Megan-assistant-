"""
File Agent - Complete file and directory operations for MEGAN
Covers: find, list, read, write, copy, move, delete, rename, organize,
        create folders, get info, search by content, open files
"""

import os
import shutil
import json
import fnmatch
import glob
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class FileAgent:
    """
    File Agent - Comprehensive file system operations.

    Capabilities:
    - Find files by name, extension, pattern, or content
    - List directory contents (with sorting)
    - Read / write text files
    - Copy files and folders
    - Move files and folders
    - Delete files and folders (with confirmation)
    - Rename files and folders
    - Create directories
    - Organize by file type into category folders
    - Get file metadata
    - Open files with default or specified app
    - Bulk operations (copy/move/delete multiple)
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
        "Documents": [".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx",
                      ".pptx", ".ppt", ".odt", ".csv", ".rtf"],
        "Images":    [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg",
                      ".webp", ".ico", ".tiff", ".raw"],
        "Videos":    [".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv",
                      ".webm", ".m4v", ".3gp"],
        "Audio":     [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"],
        "Archives":  [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"],
        "Code":      [".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp",
                      ".c", ".h", ".html", ".css", ".json", ".xml", ".yaml",
                      ".yml", ".sh", ".bat", ".ps1", ".sql", ".r", ".go",
                      ".rs", ".php", ".rb", ".swift", ".kt"],
        "Executables": [".exe", ".msi", ".apk", ".dmg", ".deb", ".rpm"],
        "Fonts":     [".ttf", ".otf", ".woff", ".woff2"],
    }

    def __init__(self, safe_mode: bool = True):
        self.safe_mode = safe_mode

    # ── Safety ────────────────────────────────────────────────────────────────

    def is_safe_path(self, path: str) -> bool:
        """Return False if path is in a restricted area (when safe_mode=True)."""
        if not self.safe_mode:
            return True
        path_lower = Path(path).resolve().as_posix().lower()
        return not any(r in path_lower for r in self.RESTRICTED_PATHS)

    def _resolve(self, path: str) -> str:
        """Expand environment variables and home dir."""
        return os.path.expandvars(os.path.expanduser(path))

    def _safe_check(self, path: str) -> Optional[str]:
        """Return error string if path is unsafe, else None."""
        if not self.is_safe_path(path):
            return "Access denied — restricted system path"
        return None

    # ── Find / List ───────────────────────────────────────────────────────────

    def find_files(
        self,
        directory: str = ".",
        pattern: Optional[str] = None,
        file_type: Optional[str] = None,
        recursive: bool = True,
        max_results: int = 100,
    ) -> Dict:
        """
        Find files in a directory by name pattern or extension.

        Args:
            directory:   Root path to search
            pattern:     Substring or glob pattern in filename (e.g. 'report' or '*.pdf')
            file_type:   Extension filter e.g. '.pdf', '.py'
            recursive:   Search subdirectories (default True)
            max_results: Cap results (default 100)
        """
        directory = self._resolve(directory)
        if err := self._safe_check(directory):
            return {"error": err}
        if not os.path.exists(directory):
            return {"error": f"Directory not found: {directory}"}

        try:
            results: List[Dict] = []
            path_obj = Path(directory)
            glob_pat = "**/*" if recursive else "*"

            for fp in path_obj.glob(glob_pat):
                if not fp.is_file():
                    continue
                name = fp.name

                # Pattern filter (glob or substring)
                if pattern:
                    if any(c in pattern for c in ["*", "?", "["]):
                        if not fnmatch.fnmatch(name.lower(), pattern.lower()):
                            continue
                    elif pattern.lower() not in name.lower():
                        continue

                # Extension filter
                if file_type:
                    ext = file_type if file_type.startswith(".") else "." + file_type
                    if fp.suffix.lower() != ext.lower():
                        continue

                stat = fp.stat()
                results.append({
                    "path":     str(fp),
                    "name":     fp.name,
                    "size_kb":  round(stat.st_size / 1024, 2),
                    "type":     fp.suffix,
                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                })

                if len(results) >= max_results:
                    break

            results.sort(key=lambda x: x["modified"], reverse=True)
            print(f"[FILE] Found {len(results)} files in {directory}")
            return {
                "status":    "success",
                "files":     results,
                "count":     len(results),
                "directory": directory,
            }

        except Exception as e:
            return {"error": str(e)}

    def list_directory(
        self,
        directory: str = ".",
        show_hidden: bool = False,
        sort_by: str = "name",
    ) -> Dict:
        """
        List directory contents.

        Args:
            directory:   Path to list
            show_hidden: Include hidden files (starting with .)
            sort_by:     'name', 'size', 'modified', 'type'
        """
        directory = self._resolve(directory)
        if err := self._safe_check(directory):
            return {"error": err}
        if not os.path.exists(directory):
            return {"error": f"Directory not found: {directory}"}

        try:
            items = []
            for name in os.listdir(directory):
                if not show_hidden and name.startswith("."):
                    continue
                item_path = os.path.join(directory, name)
                entry: Dict = {"name": name, "path": item_path}

                if os.path.isdir(item_path):
                    entry["type"]     = "folder"
                    entry["size_kb"]  = 0
                    try:
                        entry["children"] = len(os.listdir(item_path))
                    except PermissionError:
                        entry["children"] = "?"
                else:
                    size = os.path.getsize(item_path)
                    entry["type"]     = Path(name).suffix or "file"
                    entry["size_kb"]  = round(size / 1024, 2)

                try:
                    mtime = os.path.getmtime(item_path)
                    entry["modified"] = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    entry["modified"] = ""

                items.append(entry)

            # Sort
            sort_keys = {"name": "name", "size": "size_kb", "modified": "modified", "type": "type"}
            key = sort_keys.get(sort_by, "name")
            items.sort(key=lambda x: x.get(key, ""))

            folders = [i for i in items if i["type"] == "folder"]
            files   = [i for i in items if i["type"] != "folder"]

            return {
                "status":    "success",
                "directory": directory,
                "folders":   folders,
                "files":     files,
                "total":     len(items),
            }

        except PermissionError:
            return {"error": f"Permission denied: {directory}"}
        except Exception as e:
            return {"error": str(e)}

    def search_by_content(
        self,
        directory: str,
        keyword: str,
        file_type: Optional[str] = None,
        max_results: int = 20,
    ) -> Dict:
        """
        Search file contents for a keyword (text files only).
        """
        directory = self._resolve(directory)
        if err := self._safe_check(directory):
            return {"error": err}

        text_exts = {".txt", ".py", ".js", ".ts", ".html", ".css", ".json",
                     ".xml", ".yaml", ".yml", ".csv", ".md", ".log", ".bat",
                     ".sh", ".sql", ".java", ".cpp", ".c", ".h"}
        if file_type:
            text_exts = {file_type if file_type.startswith(".") else "." + file_type}

        results = []
        try:
            for fp in Path(directory).rglob("*"):
                if not fp.is_file():
                    continue
                if fp.suffix.lower() not in text_exts:
                    continue
                try:
                    with open(fp, "r", encoding="utf-8", errors="replace") as f:
                        for i, line in enumerate(f, 1):
                            if keyword.lower() in line.lower():
                                results.append({
                                    "file":    str(fp),
                                    "line_no": i,
                                    "line":    line.strip()[:200],
                                })
                                if len(results) >= max_results:
                                    break
                except Exception:
                    continue
                if len(results) >= max_results:
                    break

            return {
                "status":  "success",
                "keyword": keyword,
                "matches": results,
                "count":   len(results),
            }
        except Exception as e:
            return {"error": str(e)}

    # ── Read / Write ──────────────────────────────────────────────────────────

    def read_file(self, file_path: str, max_chars: int = 5000) -> Dict:
        """Read a text file (up to max_chars characters)."""
        file_path = self._resolve(file_path)
        if err := self._safe_check(file_path):
            return {"error": err}
        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(max_chars)
            truncated = os.path.getsize(file_path) > max_chars
            return {
                "status":    "success",
                "file":      file_path,
                "content":   content,
                "size":      os.path.getsize(file_path),
                "truncated": truncated,
            }
        except Exception as e:
            return {"error": str(e)}

    def write_file(self, file_path: str, content: str, overwrite: bool = False, append: bool = False) -> Dict:
        """Create or write a text file."""
        file_path = self._resolve(file_path)
        if err := self._safe_check(file_path):
            return {"error": err}
        if os.path.exists(file_path) and not overwrite and not append:
            return {"status": "file_exists", "message": f"File exists: {file_path}. Set overwrite=True to replace."}

        try:
            parent = os.path.dirname(file_path)
            if parent:
                os.makedirs(parent, exist_ok=True)

            mode = "a" if append else "w"
            with open(file_path, mode, encoding="utf-8") as f:
                f.write(content)

            print(f"[FILE] Written: {file_path} ({len(content)} chars)")
            return {"status": "success", "file": file_path, "size": len(content), "mode": mode}
        except Exception as e:
            return {"error": str(e)}

    # ── Copy / Move / Rename ──────────────────────────────────────────────────

    def copy(self, source: str, destination: str, overwrite: bool = False) -> Dict:
        """
        Copy a file or folder to destination.

        Args:
            source:      Path to file or folder
            destination: Target path (file or directory)
            overwrite:   Overwrite if destination exists
        """
        source      = self._resolve(source)
        destination = self._resolve(destination)

        if err := self._safe_check(source):
            return {"error": err}
        if err := self._safe_check(destination):
            return {"error": err}
        if not os.path.exists(source):
            return {"error": f"Source not found: {source}"}

        try:
            if os.path.isdir(source):
                # If destination is an existing directory, put folder inside it
                if os.path.isdir(destination):
                    final_dest = os.path.join(destination, os.path.basename(source))
                else:
                    final_dest = destination

                if os.path.exists(final_dest):
                    if not overwrite:
                        return {"status": "exists", "message": f"Destination exists: {final_dest}. Use overwrite=True."}
                    shutil.rmtree(final_dest)

                shutil.copytree(source, final_dest)
                print(f"[FILE] Copied folder: {source} -> {final_dest}")
            else:
                # File copy
                if os.path.isdir(destination):
                    final_dest = os.path.join(destination, os.path.basename(source))
                else:
                    final_dest = destination
                    os.makedirs(os.path.dirname(final_dest), exist_ok=True)

                if os.path.exists(final_dest) and not overwrite:
                    return {"status": "exists", "message": f"File exists: {final_dest}. Use overwrite=True."}

                shutil.copy2(source, final_dest)
                print(f"[FILE] Copied: {source} -> {final_dest}")
                final_dest = final_dest

            return {"status": "success", "source": source, "destination": final_dest}

        except Exception as e:
            print(f"[FILE] Copy failed: {e}")
            return {"error": str(e)}

    def move(self, source: str, destination: str, overwrite: bool = False) -> Dict:
        """
        Move a file or folder to a new location.

        Args:
            source:      Source path
            destination: Target path or directory
            overwrite:   Allow overwriting existing destination
        """
        source      = self._resolve(source)
        destination = self._resolve(destination)

        if err := self._safe_check(source):
            return {"error": err}
        if err := self._safe_check(destination):
            return {"error": err}
        if not os.path.exists(source):
            return {"error": f"Source not found: {source}"}

        try:
            # If destination is a directory, move source into it
            if os.path.isdir(destination):
                final_dest = os.path.join(destination, os.path.basename(source))
            else:
                final_dest = destination
                os.makedirs(os.path.dirname(final_dest) or ".", exist_ok=True)

            if os.path.exists(final_dest) and not overwrite:
                return {"status": "exists", "message": f"Destination exists: {final_dest}. Use overwrite=True."}

            if os.path.exists(final_dest):
                if os.path.isdir(final_dest):
                    shutil.rmtree(final_dest)
                else:
                    os.remove(final_dest)

            shutil.move(source, final_dest)
            print(f"[FILE] Moved: {source} -> {final_dest}")
            return {"status": "success", "source": source, "destination": final_dest}

        except Exception as e:
            print(f"[FILE] Move failed: {e}")
            return {"error": str(e)}

    def rename(self, source: str, new_name: str) -> Dict:
        """
        Rename a file or folder (new_name is just the name, not full path).

        Args:
            source:   Full path to file/folder
            new_name: New name (without path). Can also be a full new path.
        """
        source = self._resolve(source)
        if err := self._safe_check(source):
            return {"error": err}
        if not os.path.exists(source):
            return {"error": f"Not found: {source}"}

        try:
            if os.path.sep in new_name or "/" in new_name:
                # new_name is a full path
                dest = self._resolve(new_name)
            else:
                dest = os.path.join(os.path.dirname(source), new_name)

            if os.path.exists(dest):
                return {"error": f"Name already exists: {dest}"}

            os.rename(source, dest)
            print(f"[FILE] Renamed: {source} -> {dest}")
            return {"status": "success", "old_name": source, "new_name": dest}

        except Exception as e:
            return {"error": str(e)}

    # ── Delete ────────────────────────────────────────────────────────────────

    def delete(self, path: str, confirm: bool = False) -> Dict:
        """
        Delete a file OR folder (with confirmation).

        Args:
            path:    Path to file or folder
            confirm: Must be True to actually delete
        """
        path = self._resolve(path)
        is_dir = os.path.isdir(path)
        kind   = "folder and ALL its contents" if is_dir else "file"

        if not confirm:
            return {
                "status":  "needs_confirmation",
                "message": f"Are you sure you want to delete the {kind}: '{path}'?",
                "path":    path,
            }

        if err := self._safe_check(path):
            return {"error": err}
        if not os.path.exists(path):
            return {"error": f"Not found: {path}"}

        try:
            if is_dir:
                shutil.rmtree(path)
                print(f"[FILE] Deleted folder: {path}")
            else:
                os.remove(path)
                print(f"[FILE] Deleted file: {path}")
            return {"status": "success", "message": f"Deleted: {path}"}
        except Exception as e:
            return {"error": str(e)}

    def bulk_delete(self, paths: List[str], confirm: bool = False) -> Dict:
        """Delete multiple files/folders at once."""
        if not confirm:
            return {
                "status":  "needs_confirmation",
                "message": f"Delete {len(paths)} items?",
                "items":   paths,
            }
        results = {"deleted": [], "errors": []}
        for p in paths:
            r = self.delete(p, confirm=True)
            if r.get("status") == "success":
                results["deleted"].append(p)
            else:
                results["errors"].append({"path": p, "error": r.get("error")})
        results["status"] = "success" if not results["errors"] else "partial"
        return results

    # ── Create ────────────────────────────────────────────────────────────────

    def create_folder(self, path: str, parents: bool = True) -> Dict:
        """Create a folder (and parents if needed)."""
        path = self._resolve(path)
        if err := self._safe_check(path):
            return {"error": err}
        try:
            os.makedirs(path, exist_ok=True) if parents else os.mkdir(path)
            print(f"[FILE] Created folder: {path}")
            return {"status": "success", "folder": path}
        except FileExistsError:
            return {"status": "exists", "message": f"Folder already exists: {path}"}
        except Exception as e:
            return {"error": str(e)}

    def create_file(self, file_path: str, content: str = "", overwrite: bool = False) -> Dict:
        """Create a new file with optional content."""
        return self.write_file(file_path, content, overwrite=overwrite)

    # ── Organize ─────────────────────────────────────────────────────────────

    def organize_directory(
        self,
        directory: str,
        confirm: bool = False,
        dry_run: bool = False,
    ) -> Dict:
        """
        Organize files in a directory into category sub-folders by extension.

        Args:
            directory: Folder to organize
            confirm:   Must be True to perform actual moves
            dry_run:   If True, show what WOULD be moved without doing it
        """
        directory = self._resolve(directory)

        if not dry_run and not confirm:
            # Preview first
            preview = self._organize_preview(directory)
            return {
                "status":  "needs_confirmation",
                "message": f"Organize {preview['total']} files in '{directory}' into category folders?",
                "preview": preview,
            }

        if err := self._safe_check(directory):
            return {"error": err}
        if not os.path.exists(directory):
            return {"error": f"Directory not found: {directory}"}

        moved   = []
        skipped = []
        errors  = []

        try:
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if not os.path.isfile(item_path):
                    continue

                ext = Path(item).suffix.lower()
                category = None
                for cat, exts in self.FILE_CATEGORIES.items():
                    if ext in exts:
                        category = cat
                        break

                if not category:
                    skipped.append(item)
                    continue

                dest_dir  = os.path.join(directory, category)
                dest_path = os.path.join(dest_dir, item)

                if dry_run:
                    moved.append({"file": item, "to": category})
                    continue

                try:
                    os.makedirs(dest_dir, exist_ok=True)
                    shutil.move(item_path, dest_path)
                    moved.append({"file": item, "to": category})
                except Exception as e:
                    errors.append({"file": item, "error": str(e)})

            print(f"[FILE] Organized {len(moved)} files in {directory}")
            return {
                "status":    "dry_run" if dry_run else "success",
                "moved":     moved,
                "skipped":   skipped,
                "errors":    errors,
                "total":     len(moved),
                "directory": directory,
            }

        except Exception as e:
            return {"error": str(e)}

    def _organize_preview(self, directory: str) -> Dict:
        """Preview what organize_directory would do."""
        categories: Dict[str, List[str]] = {}
        total = 0
        try:
            for item in os.listdir(directory):
                if not os.path.isfile(os.path.join(directory, item)):
                    continue
                ext = Path(item).suffix.lower()
                for cat, exts in self.FILE_CATEGORIES.items():
                    if ext in exts:
                        categories.setdefault(cat, []).append(item)
                        total += 1
                        break
        except Exception:
            pass
        return {"categories": categories, "total": total}

    def organize_by_date(self, directory: str, confirm: bool = False) -> Dict:
        """Organize files into year/month sub-folders based on modification date."""
        directory = self._resolve(directory)
        if not confirm:
            return {
                "status":  "needs_confirmation",
                "message": f"Organize files in '{directory}' into date folders (Year/Month)?",
            }
        if err := self._safe_check(directory):
            return {"error": err}

        moved = []
        errors = []
        try:
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if not os.path.isfile(item_path):
                    continue
                mtime    = datetime.fromtimestamp(os.path.getmtime(item_path))
                dest_dir = os.path.join(directory, str(mtime.year), mtime.strftime("%m-%B"))
                dest     = os.path.join(dest_dir, item)
                try:
                    os.makedirs(dest_dir, exist_ok=True)
                    shutil.move(item_path, dest)
                    moved.append({"file": item, "to": dest_dir})
                except Exception as e:
                    errors.append({"file": item, "error": str(e)})

            return {"status": "success", "moved": len(moved), "errors": errors}
        except Exception as e:
            return {"error": str(e)}

    # ── Bulk Copy / Move ──────────────────────────────────────────────────────

    def bulk_copy(self, sources: List[str], destination: str, overwrite: bool = False) -> Dict:
        """Copy multiple files/folders to a destination directory."""
        results = {"copied": [], "errors": []}
        for src in sources:
            r = self.copy(src, destination, overwrite=overwrite)
            if r.get("status") == "success":
                results["copied"].append(r["destination"])
            else:
                results["errors"].append({"source": src, "error": r.get("error")})
        results["status"] = "success" if not results["errors"] else "partial"
        return results

    def bulk_move(self, sources: List[str], destination: str, overwrite: bool = False) -> Dict:
        """Move multiple files/folders to a destination directory."""
        results = {"moved": [], "errors": []}
        for src in sources:
            r = self.move(src, destination, overwrite=overwrite)
            if r.get("status") == "success":
                results["moved"].append(r["destination"])
            else:
                results["errors"].append({"source": src, "error": r.get("error")})
        results["status"] = "success" if not results["errors"] else "partial"
        return results

    # ── File Info ─────────────────────────────────────────────────────────────

    def get_file_info(self, file_path: str) -> Dict:
        """Return detailed metadata for a file or folder."""
        file_path = self._resolve(file_path)
        if not os.path.exists(file_path):
            return {"error": f"Not found: {file_path}"}

        try:
            stat = os.stat(file_path)
            info = {
                "status":       "success",
                "path":         file_path,
                "name":         os.path.basename(file_path),
                "type":         Path(file_path).suffix if os.path.isfile(file_path) else "folder",
                "size_bytes":   stat.st_size,
                "size_kb":      round(stat.st_size / 1024, 2),
                "created":      datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
                "modified":     datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "is_file":      os.path.isfile(file_path),
                "is_directory": os.path.isdir(file_path),
            }
            if os.path.isdir(file_path):
                try:
                    entries = os.listdir(file_path)
                    info["children_count"] = len(entries)
                except PermissionError:
                    info["children_count"] = "?"
            return info
        except Exception as e:
            return {"error": str(e)}

    def get_disk_usage(self, path: str = ".") -> Dict:
        """Get disk usage for a path."""
        path = self._resolve(path)
        try:
            total_size = 0
            file_count = 0
            for root, _, files in os.walk(path):
                for f in files:
                    try:
                        fp = os.path.join(root, f)
                        total_size += os.path.getsize(fp)
                        file_count += 1
                    except Exception:
                        pass
            return {
                "status":    "success",
                "path":      path,
                "total_mb":  round(total_size / 1e6, 2),
                "file_count": file_count,
            }
        except Exception as e:
            return {"error": str(e)}

    # ── Open File ─────────────────────────────────────────────────────────────

    def open_file(self, file_path: str) -> Dict:
        """Open a file with its default application."""
        file_path = self._resolve(file_path)
        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}
        try:
            import sys
            if sys.platform == "win32":
                os.startfile(file_path)
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", file_path])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", file_path])
            return {"status": "success", "file": file_path}
        except Exception as e:
            return {"error": str(e)}


# ─── Standalone Test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    agent = FileAgent(safe_mode=True)

    print("\n--- List Directory ---")
    r = agent.list_directory(".", sort_by="type")
    print(f"Folders: {len(r.get('folders', []))}, Files: {len(r.get('files', []))}")

    print("\n--- Find .py files ---")
    r = agent.find_files(".", file_type=".py", recursive=False)
    print(f"Found: {r.get('count')} python files")

    print("\n--- File Info ---")
    r = agent.get_file_info(".")
    print(r)
