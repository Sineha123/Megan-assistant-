"""
File Agent - Handles file and system operations
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import json


class FileAgent:
    """
    File Agent - Manages file operations
    
    Capabilities:
    - Find files by name/type
    - List directory contents
    - Delete files
    - Organize files
    - Edit text files
    - Create files
    - Get file info
    
    Limitations:
    - Cannot modify system files
    - Cannot access restricted directories
    """
    
    def __init__(self, safe_mode: bool = True):
        self.safe_mode = safe_mode
        self.restricted_paths = [
            "/System",
            "/Library",
            "C:\\Windows",
            "C:\\Program Files",
            "/etc",
            "/var",
            "/usr/bin"
        ]
    
    def is_safe_path(self, path: str) -> bool:
        """Check if path is safe to access"""
        if not self.safe_mode:
            return True
        
        path_lower = path.lower()
        for restricted in self.restricted_paths:
            if restricted.lower() in path_lower:
                return False
        return True
    
    def find_files(
        self,
        directory: str = ".",
        pattern: Optional[str] = None,
        file_type: Optional[str] = None,
        recursive: bool = True
    ) -> Dict:
        """
        Find files matching criteria
        
        Args:
            directory: Search directory
            pattern: Filename pattern/substring
            file_type: File extension (e.g., '.pdf', '.txt')
            recursive: Search subdirectories
        
        Returns:
            Dictionary with found files
        """
        try:
            print(f"[FILE] Searching for files in: {directory}")
            
            if not self.is_safe_path(directory):
                return {"error": "Access denied - restricted path"}
            
            if not os.path.exists(directory):
                return {"error": f"Directory not found: {directory}"}
            
            results = []
            
            # Use glob for searching
            path_obj = Path(directory)
            
            if recursive:
                search_pattern = "**/*"
            else:
                search_pattern = "*"
            
            for file_path in path_obj.glob(search_pattern):
                # Apply filters
                if pattern and pattern.lower() not in file_path.name.lower():
                    continue
                
                if file_type and not file_path.suffix.lower() == file_type.lower():
                    continue
                
                if file_path.is_file():
                    results.append({
                        "path": str(file_path),
                        "name": file_path.name,
                        "size": file_path.stat().st_size,
                        "type": file_path.suffix,
                        "modified": datetime.fromtimestamp(
                            file_path.stat().st_mtime
                        ).isoformat()
                    })
            
            print(f"[FILE] Found {len(results)} files")
            
            return {
                "status": "success",
                "files": results,
                "count": len(results)
            }
        
        except Exception as e:
            print(f"[ERROR] File search failed: {str(e)}")
            return {"error": str(e)}
    
    def list_directory(self, directory: str = ".") -> Dict:
        """
        List contents of directory
        """
        try:
            if not self.is_safe_path(directory):
                return {"error": "Access denied"}
            
            if not os.path.exists(directory):
                return {"error": f"Directory not found: {directory}"}
            
            items = []
            
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                
                if os.path.isdir(item_path):
                    items.append({
                        "name": item,
                        "type": "directory",
                        "path": item_path
                    })
                else:
                    items.append({
                        "name": item,
                        "type": "file",
                        "path": item_path,
                        "size": os.path.getsize(item_path)
                    })
            
            return {
                "status": "success",
                "directory": directory,
                "items": items,
                "count": len(items)
            }
        
        except Exception as e:
            print(f"[ERROR] Directory listing failed: {str(e)}")
            return {"error": str(e)}
    
    def delete_file(self, file_path: str, confirm: bool = False) -> Dict:
        """
        Delete a file
        
        Args:
            file_path: Path to file
            confirm: User confirmation
        """
        try:
            if not confirm:
                return {
                    "status": "needs_confirmation",
                    "message": f"Delete this file? {file_path}",
                    "file": file_path
                }
            
            if not self.is_safe_path(file_path):
                return {"error": "Cannot delete - restricted path"}
            
            if not os.path.exists(file_path):
                return {"error": "File not found"}
            
            if os.path.isdir(file_path):
                return {"error": "Use delete_directory for folders"}
            
            os.remove(file_path)
            print(f"[FILE] Deleted: {file_path}")
            
            return {
                "status": "success",
                "message": f"File deleted: {file_path}"
            }
        
        except Exception as e:
            print(f"[ERROR] Delete failed: {str(e)}")
            return {"error": str(e)}
    
    def delete_directory(self, directory: str, confirm: bool = False) -> Dict:
        """
        Delete a directory and its contents
        """
        try:
            if not confirm:
                return {
                    "status": "needs_confirmation",
                    "message": f"Delete this folder and all contents? {directory}",
                    "directory": directory
                }
            
            if not self.is_safe_path(directory):
                return {"error": "Cannot delete - restricted path"}
            
            if not os.path.exists(directory):
                return {"error": "Directory not found"}
            
            shutil.rmtree(directory)
            print(f"[FILE] Deleted directory: {directory}")
            
            return {
                "status": "success",
                "message": f"Directory deleted: {directory}"
            }
        
        except Exception as e:
            print(f"[ERROR] Directory deletion failed: {str(e)}")
            return {"error": str(e)}
    
    def read_file(self, file_path: str) -> Dict:
        """
        Read file contents (text files only)
        """
        try:
            if not self.is_safe_path(file_path):
                return {"error": "Access denied"}
            
            if not os.path.exists(file_path):
                return {"error": "File not found"}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "status": "success",
                "file": file_path,
                "content": content,
                "size": len(content)
            }
        
        except Exception as e:
            print(f"[ERROR] File read failed: {str(e)}")
            return {"error": str(e)}
    
    def write_file(
        self,
        file_path: str,
        content: str,
        overwrite: bool = False
    ) -> Dict:
        """
        Create or write to file
        """
        try:
            if not self.is_safe_path(file_path):
                return {"error": "Access denied"}
            
            if os.path.exists(file_path) and not overwrite:
                return {
                    "status": "file_exists",
                    "message": f"File already exists: {file_path}"
                }
            
            # Create directories if needed
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"[FILE] File created: {file_path}")
            
            return {
                "status": "success",
                "message": f"File created: {file_path}",
                "file": file_path,
                "size": len(content)
            }
        
        except Exception as e:
            print(f"[ERROR] File write failed: {str(e)}")
            return {"error": str(e)}
    
    def organize_directory(
        self,
        directory: str,
        confirm: bool = False
    ) -> Dict:
        """
        Organize files by type into subdirectories
        """
        try:
            if not confirm:
                return {
                    "status": "needs_confirmation",
                    "message": f"Organize files in {directory}?",
                    "directory": directory
                }
            
            if not self.is_safe_path(directory):
                return {"error": "Access denied"}
            
            if not os.path.exists(directory):
                return {"error": "Directory not found"}
            
            organized = 0
            
            # Define categories
            categories = {
                "Documents": [".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx"],
                "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp"],
                "Videos": [".mp4", ".avi", ".mov", ".mkv"],
                "Audio": [".mp3", ".wav", ".flac", ".aac"],
                "Archives": [".zip", ".rar", ".7z", ".tar"],
                "Code": [".py", ".js", ".java", ".cpp", ".html", ".css"]
            }
            
            # Move files
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                
                if os.path.isfile(item_path):
                    ext = Path(item).suffix.lower()
                    
                    for category, extensions in categories.items():
                        if ext in extensions:
                            category_path = os.path.join(directory, category)
                            os.makedirs(category_path, exist_ok=True)
                            
                            new_path = os.path.join(category_path, item)
                            shutil.move(item_path, new_path)
                            organized += 1
                            break
            
            print(f"[FILE] Organized {organized} files")
            
            return {
                "status": "success",
                "message": f"Organized {organized} files",
                "directory": directory
            }
        
        except Exception as e:
            print(f"[ERROR] Organization failed: {str(e)}")
            return {"error": str(e)}
    
    def get_file_info(self, file_path: str) -> Dict:
        """
        Get detailed file information
        """
        try:
            if not os.path.exists(file_path):
                return {"error": "File not found"}
            
            stat = os.stat(file_path)
            
            return {
                "status": "success",
                "file": file_path,
                "name": os.path.basename(file_path),
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "is_file": os.path.isfile(file_path),
                "is_directory": os.path.isdir(file_path)
            }
        
        except Exception as e:
            return {"error": str(e)}


# Test
if __name__ == "__main__":
    agent = FileAgent(safe_mode=True)
    
    # Test: Find Python files
    result = agent.find_files(".", file_type=".py")
    print(json.dumps(result, indent=2))
    
    # Test: List home directory
    result = agent.list_directory(".")
    print(json.dumps(result, indent=2))
