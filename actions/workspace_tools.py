"""
actions/workspace_tools.py
===============================================================================
Workspace & File Automation Suite:
- Deep recursive workspace file searching with glob/regex filters
- Safe file creation, reading, surgical editing, and deletion
- Automated repository & workspace backup engine with SHA-256 integrity hash
- Isolated scratch workspace provisioning and repository clutter organization
===============================================================================
"""

import os
import sys
import fnmatch
import hashlib
import zipfile
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import send2trash
    _SEND2TRASH_AVAILABLE = True
except ImportError:
    _SEND2TRASH_AVAILABLE = False


_BASE_DIR = Path(__file__).resolve().parent.parent
_DEFAULT_BACKUP_DIR = _BASE_DIR / "backups"
_DEFAULT_SCRATCH_DIR = _BASE_DIR / "scratch"

_DEFAULT_EXCLUDES = {
    ".git", "__pycache__", ".venv", ".venv_old", "node_modules",
    ".pytest_cache", ".gemini", ".claude", "backups", ".agents",
    "scratch", "dist", "build", ".next", ".cache", "vendor",
    "ai assistant_old", "worldmonitor-main", "assets", "logs", "odysseus",
    "MQ3 TRADING BOT", "apps", "database", "data", "content", "media", "docs"
}

_CORE_BACKUP_DIRS = [
    "actions", "bootstrap", "config", "core", "memory",
    "security", "ui", "tests", "trading", "agent"
]


# =============================================================================
# Helper Utilities
# =============================================================================

def _resolve_workspace_path(path_str: Union[str, Path, None], default_base: Optional[Path] = None) -> Path:
    """Resolves a user-supplied path relative to workspace or absolute."""
    base = default_base or _BASE_DIR
    if not path_str:
        return base
    p = Path(path_str)
    if p.is_absolute():
        return p
    return (base / p).resolve()


def _calculate_sha256(file_path: Path) -> str:
    """Calculates SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


# =============================================================================
# 1. Search Files & Workspaces
# =============================================================================

def search_workspace(
    pattern: str = "*",
    root_dir: Optional[Union[str, Path]] = None,
    max_results: int = 50,
    recursive: bool = True,
    file_types: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Searches workspace directory for files matching pattern or extension.
    Uses directory subtree pruning for sub-millisecond lookups.
    """
    root = _resolve_workspace_path(root_dir)
    if not root.exists():
        return {
            "status": "error",
            "detail": f"Root directory does not exist: {root}",
            "matches": [],
            "total_found": 0
        }

    matches = []
    clean_pattern = pattern.strip() if pattern else "*"
    if not clean_pattern:
        clean_pattern = "*"

    valid_exts = {ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in file_types} if file_types else None
    count = 0

    if recursive:
        for r, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in _DEFAULT_EXCLUDES and not d.startswith(".")]
            for name in files:
                if valid_exts and not any(name.lower().endswith(ext) for ext in valid_exts):
                    continue
                if clean_pattern == "*" or fnmatch.fnmatch(name.lower(), clean_pattern.lower()) or (clean_pattern.lower() in name.lower()):
                    item = Path(r) / name
                    try:
                        stat = item.stat()
                        matches.append({
                            "path": str(item.resolve()),
                            "relative_path": str(item.relative_to(root)),
                            "name": name,
                            "size_bytes": stat.st_size,
                            "is_dir": False,
                            "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                        })
                        count += 1
                        if count >= max_results:
                            break
                    except (PermissionError, OSError):
                        continue
            if count >= max_results:
                break
    else:
        for item in root.glob("*"):
            if item.name in _DEFAULT_EXCLUDES or item.name.startswith("."):
                continue
            if valid_exts and item.is_file() and item.suffix.lower() not in valid_exts:
                continue
            if clean_pattern == "*" or fnmatch.fnmatch(item.name.lower(), clean_pattern.lower()) or (clean_pattern.lower() in item.name.lower()):
                try:
                    stat = item.stat()
                    matches.append({
                        "path": str(item.resolve()),
                        "relative_path": str(item.relative_to(root)),
                        "name": item.name,
                        "size_bytes": stat.st_size if item.is_file() else 0,
                        "is_dir": item.is_dir(),
                        "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                    })
                    count += 1
                    if count >= max_results:
                        break
                except (PermissionError, OSError):
                    continue

    return {
        "status": "success",
        "root_dir": str(root.resolve()),
        "pattern": clean_pattern,
        "total_found": len(matches),
        "matches": matches,
        "detail": f"Found {len(matches)} item(s) matching '{clean_pattern}' in {root.name}."
    }


# =============================================================================
# 2. File Operations (Create, Read, Edit, Delete)
# =============================================================================

def create_workspace_file(path: Union[str, Path], content: str = "", overwrite: bool = False) -> Dict[str, Any]:
    """
    Safely creates a new file with specified UTF-8 content.
    """
    target = _resolve_workspace_path(path)
    if target.exists() and not overwrite:
        return {
            "status": "error",
            "detail": f"File already exists: {target}. Set overwrite=True to overwrite.",
            "file_path": str(target.resolve())
        }

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {
            "status": "success",
            "file_path": str(target.resolve()),
            "size_bytes": len(content.encode("utf-8")),
            "detail": f"File created successfully at {target.name} ({len(content)} chars)."
        }
    except Exception as e:
        return {
            "status": "error",
            "detail": f"Failed to create file: {e}",
            "file_path": str(target.resolve())
        }


def read_workspace_file(path: Union[str, Path], max_lines: int = 500, start_line: int = 1) -> Dict[str, Any]:
    """
    Safely reads file lines.
    """
    target = _resolve_workspace_path(path)
    if not target.exists() or not target.is_file():
        return {
            "status": "error",
            "detail": f"File not found: {target}",
            "file_path": str(target.resolve())
        }

    try:
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        total_lines = len(lines)
        start_idx = max(0, start_line - 1)
        end_idx = min(total_lines, start_idx + max_lines)
        sliced = lines[start_idx:end_idx]
        return {
            "status": "success",
            "file_path": str(target.resolve()),
            "total_lines": total_lines,
            "returned_lines": len(sliced),
            "start_line": start_line,
            "content": "\\n".join(sliced),
            "detail": f"Read {len(sliced)}/{total_lines} line(s) from {target.name}."
        }
    except Exception as e:
        return {
            "status": "error",
            "detail": f"Failed to read file: {e}",
            "file_path": str(target.resolve())
        }


def edit_workspace_file(
    path: Union[str, Path],
    target_content: str,
    replacement_content: str,
    allow_multiple: bool = False
) -> Dict[str, Any]:
    """
    Performs surgical replacement of content in a workspace file.
    """
    target = _resolve_workspace_path(path)
    if not target.exists() or not target.is_file():
        return {
            "status": "error",
            "detail": f"File not found: {target}",
            "file_path": str(target.resolve())
        }

    try:
        text = target.read_text(encoding="utf-8")
        occurrences = text.count(target_content)
        if occurrences == 0:
            return {
                "status": "error",
                "detail": f"Target content not found in file {target.name}.",
                "file_path": str(target.resolve())
            }

        if occurrences > 1 and not allow_multiple:
            return {
                "status": "error",
                "detail": f"Found {occurrences} occurrences of target content. Set allow_multiple=True to replace all.",
                "file_path": str(target.resolve())
            }

        new_text = text.replace(target_content, replacement_content) if allow_multiple else text.replace(target_content, replacement_content, 1)
        target.write_text(new_text, encoding="utf-8")

        return {
            "status": "success",
            "file_path": str(target.resolve()),
            "replacements_made": occurrences if allow_multiple else 1,
            "detail": f"Successfully edited {target.name} ({occurrences if allow_multiple else 1} replacement(s))."
        }
    except Exception as e:
        return {
            "status": "error",
            "detail": f"Failed to edit file: {e}",
            "file_path": str(target.resolve())
        }


def delete_workspace_file(path: Union[str, Path], send_to_trash: bool = True, force: bool = False) -> Dict[str, Any]:
    """
    Safely deletes file or directory with recycle bin support.
    """
    target = _resolve_workspace_path(path)
    if not target.exists():
        return {
            "status": "error",
            "detail": f"Target does not exist: {target}",
            "file_path": str(target.resolve())
        }

    if target.resolve() == _BASE_DIR.resolve():
        return {
            "status": "blocked",
            "detail": "Deletion of workspace root is strictly prohibited.",
            "file_path": str(target.resolve())
        }

    try:
        if send_to_trash and _SEND2TRASH_AVAILABLE:
            send2trash.send2trash(str(target))
            return {
                "status": "success",
                "file_path": str(target.resolve()),
                "method": "recycle_bin",
                "detail": f"Moved '{target.name}' to Recycle Bin."
            }
        else:
            if target.is_dir():
                shutil.rmtree(str(target))
            else:
                target.unlink()
            return {
                "status": "success",
                "file_path": str(target.resolve()),
                "method": "permanent_unlink",
                "detail": f"Permanently deleted '{target.name}'."
            }
    except Exception as e:
        return {
            "status": "error",
            "detail": f"Failed to delete target: {e}",
            "file_path": str(target.resolve())
        }


# =============================================================================
# 3. Repository & Workspace Backup Engine
# =============================================================================

def backup_repository(
    source_dir: Optional[Union[str, Path]] = None,
    backup_dest: Optional[Union[str, Path]] = None,
    zip_archive: bool = True,
    exclude_dirs: Optional[List[str]] = None,
    max_file_size_mb: float = 25.0
) -> Dict[str, Any]:
    """
    Creates a full compressed archive backup of workspace repository.
    Generates SHA-256 hash receipt, file catalog, and size breakdown.
    """
    src = _resolve_workspace_path(source_dir) if source_dir else _BASE_DIR
    dest_dir = _resolve_workspace_path(backup_dest, default_base=_DEFAULT_BACKUP_DIR)
    dest_dir.mkdir(parents=True, exist_ok=True)

    if not src.exists():
        return {
            "status": "error",
            "detail": f"Source directory not found: {src}"
        }

    excludes = set(_DEFAULT_EXCLUDES)
    if exclude_dirs:
        excludes.update(exclude_dirs)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive_name = f"backup_{src.name}_{ts}.zip"
    archive_path = dest_dir / archive_name

    file_count = 0
    total_uncompressed_bytes = 0
    max_size_bytes = int(max_file_size_mb * 1024 * 1024)

    try:
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as zf:
            is_root_workspace = (source_dir is None) or (src.resolve() == _BASE_DIR.resolve())

            if is_root_workspace:
                root_files = [f for f in _BASE_DIR.iterdir() if f.is_file() and f.suffix in [".py", ".md", ".json", ".bat", ".ps1", ".txt", ".ini", ".env"]]
                for rf in root_files:
                    try:
                        zf.write(rf, arcname=rf.name)
                        file_count += 1
                        total_uncompressed_bytes += rf.stat().st_size
                    except (PermissionError, OSError):
                        continue

                for cd in _CORE_BACKUP_DIRS:
                    cd_path = _BASE_DIR / cd
                    if cd_path.exists():
                        for root, dirs, files in os.walk(cd_path):
                            dirs[:] = [d for d in dirs if d not in excludes and not d.startswith(".")]
                            for file in files:
                                if file.endswith((".pyc", ".tmp", ".zip", ".tar.gz")):
                                    continue
                                full_file = Path(root) / file
                                try:
                                    sz = full_file.stat().st_size
                                    if sz > max_size_bytes:
                                        continue
                                    rel_path = full_file.relative_to(_BASE_DIR)
                                    zf.write(full_file, arcname=str(rel_path))
                                    file_count += 1
                                    total_uncompressed_bytes += sz
                                except (PermissionError, OSError):
                                    continue
            else:
                for root, dirs, files in os.walk(src):
                    dirs[:] = [d for d in dirs if d not in excludes and not d.startswith(".")]
                    for file in files:
                        if file.endswith((".pyc", ".tmp", ".zip", ".tar.gz", ".mp3", ".png", ".jpg", ".wav")):
                            continue
                        full_file = Path(root) / file
                        try:
                            sz = full_file.stat().st_size
                            if sz > max_size_bytes:
                                continue
                            rel_path = full_file.relative_to(src)
                            zf.write(full_file, arcname=str(rel_path))
                            file_count += 1
                            total_uncompressed_bytes += sz
                        except (PermissionError, OSError):
                            continue

        archive_size = archive_path.stat().st_size
        sha256_hash = _calculate_sha256(archive_path)

        return {
            "status": "success",
            "action": "backup_repo",
            "archive_path": str(archive_path.resolve()),
            "archive_name": archive_name,
            "source_dir": str(src.resolve()),
            "file_count": file_count,
            "uncompressed_bytes": total_uncompressed_bytes,
            "archive_size_bytes": archive_size,
            "compression_ratio": round((1 - (archive_size / max(1, total_uncompressed_bytes))) * 100, 2),
            "sha256": sha256_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "detail": (
                f"Repository backup created: {archive_name} ({file_count} files, "
                f"{archive_size / (1024**2):.2f} MB, SHA256: {sha256_hash[:12]}...)."
            )
        }
    except Exception as e:
        return {
            "status": "error",
            "detail": f"Backup generation failed: {e}",
            "archive_path": str(archive_path.resolve()) if archive_path.exists() else None
        }


# =============================================================================
# 4. Scratch Workspace Provisioner
# =============================================================================

def create_scratch_workspace(name: Optional[str] = None, base_dir: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """
    Provisions an isolated scratch workspace for experiments or temp tasks.
    """
    base = _resolve_workspace_path(base_dir, default_base=_DEFAULT_SCRATCH_DIR)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    folder_name = f"scratch_{name}_{ts}" if name else f"scratch_{ts}"
    scratch_path = base / folder_name
    scratch_path.mkdir(parents=True, exist_ok=True)

    readme_path = scratch_path / "README.md"
    readme_content = f"""# Scratch Workspace: {folder_name}
Created: {datetime.now(timezone.utc).isoformat()}
Purpose: Isolated workspace environment for sovereign automation and testing.
"""
    readme_path.write_text(readme_content, encoding="utf-8")

    return {
        "status": "success",
        "action": "create_scratch",
        "workspace_path": str(scratch_path.resolve()),
        "name": folder_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "detail": f"Scratch workspace provisioned at {scratch_path.name}."
    }


# =============================================================================
# 5. Workspace Clutter Organizer
# =============================================================================

def organize_workspace(target_dir: Optional[Union[str, Path]] = None, clean_temp: bool = True) -> Dict[str, Any]:
    """
    Scans workspace, cleans temporary build artifacts and summaries.
    """
    target = _resolve_workspace_path(target_dir)
    if not target.exists():
        return {"status": "error", "detail": f"Target directory not found: {target}"}

    cleaned_files = 0
    cleaned_bytes = 0

    if clean_temp:
        for root, dirs, files in os.walk(target):
            if os.path.basename(root) == "__pycache__":
                for f in files:
                    fp = Path(root) / f
                    try:
                        cleaned_bytes += fp.stat().st_size
                        fp.unlink()
                        cleaned_files += 1
                    except Exception:
                        pass

    return {
        "status": "success",
        "action": "organize_workspace",
        "target_dir": str(target.resolve()),
        "cleaned_files": cleaned_files,
        "cleaned_bytes": cleaned_bytes,
        "detail": f"Workspace organization completed. Cleaned {cleaned_files} temporary artifact(s)."
    }


# =============================================================================
# 6. Workspace Master Dispatcher
# =============================================================================

def handle_workspace_action(
    action: str,
    target: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Dispatches file and workspace automation requests.
    """
    params = parameters or {}
    mode = target or params.get("mode", "search")
    path_param = params.get("path_or_pattern", "")

    if mode == "backup":
        return backup_repository(source_dir=path_param or None)

    elif mode == "search":
        pattern = path_param or params.get("pattern", "*")
        return search_workspace(pattern=pattern)

    elif mode == "create":
        filename = path_param or params.get("filename", "notes.txt")
        content = params.get("content", "")
        return create_workspace_file(path=filename, content=content, overwrite=params.get("overwrite", False))

    elif mode == "read":
        filename = path_param or params.get("filename", "")
        return read_workspace_file(path=filename)

    elif mode == "edit":
        filename = path_param or params.get("filename", "")
        target_str = params.get("target_content", "")
        rep_str = params.get("replacement_content", "")
        return edit_workspace_file(path=filename, target_content=target_str, replacement_content=rep_str)

    elif mode == "delete":
        filename = path_param or params.get("filename", "")
        return delete_workspace_file(path=filename)

    elif mode == "scratch":
        name = path_param or params.get("name", "temp")
        return create_scratch_workspace(name=name)

    elif mode == "organize":
        return organize_workspace(target_dir=path_param or _BASE_DIR)

    return {
        "status": "error",
        "detail": f"Unsupported workspace operation mode: '{mode}'"
    }
