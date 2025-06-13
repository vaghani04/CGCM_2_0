from src.app.config.settings import settings
from pathlib import Path
import asyncio

async def get_directory_structure(codebase_path: str, depth: int = 2) -> str:
    """
    Async version of directory structure scanner.
    Returns directory structure as a formatted string.
    Ignores directories from settings.REPO_MAP_EXCLUDED_DIRS
    Only includes .py, .js, .ts files and directories containing them.
    """
    base_path = Path(codebase_path).resolve()
    
    def is_supported_file(file_path: Path) -> bool:
        """Check if file has supported extension"""
        return file_path.suffix.lower() in settings.REPO_MAP_SUPPORTED_EXTENSIONS
    
    async def traverse(path: Path, current_depth: int) -> list[str]:
        if current_depth > depth:
            return []
        
        lines = []
        prefix = '│   ' * (current_depth - 1) + ('├── ' if current_depth > 0 else '')
        
        try:
            items = await asyncio.to_thread(lambda: sorted(path.iterdir(), key=lambda x: x.name))
        except (PermissionError, OSError):
            return []
        
        for item in items:
            if item.is_dir():
                if item.name in settings.REPO_MAP_EXCLUDED_DIRS:
                    continue

                sub_lines = await traverse(item, current_depth + 1)
                if sub_lines:
                    lines.append(f"{prefix}{item.name}/")
                    lines.extend(sub_lines)
            
            elif item.is_file() and is_supported_file(item):
                lines.append(f"{prefix}{item.name}")
        
        return lines
    
    structure_lines = [base_path.name] + await traverse(base_path, 1)
    
    return "\n".join(structure_lines)