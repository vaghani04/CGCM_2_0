import os
import hashlib
from typing import Dict, List, Tuple, Optional
from src.app.utils.hash_calculator import calculate_hash

class MerkleNode:
    """Node in the Merkle Tree"""
    def __init__(self, hash_value: bytes, left=None, right=None):
        self.hash = hash_value
        self.left = left
        self.right = right

class MerkleTree:
    """Custom implementation of a Merkle Tree"""
    def __init__(self, leaves: List[bytes]):
        if not leaves:
            leaves = [b'empty']  # Default value for empty tree
        
        # Ensure all leaves are bytes
        self.leaves = [leaf if isinstance(leaf, bytes) else bytes(leaf) for leaf in leaves]
        
        # Build the tree
        self.root_node = self._build_tree(self.leaves)
        self._root_hash = self.root_node.hash if self.root_node else None
    
    def _build_tree(self, nodes: List[bytes]) -> Optional[MerkleNode]:
        """Build the Merkle Tree from the leaves"""
        if not nodes:
            return None
            
        # Convert raw bytes into MerkleNodes
        node_objects = [MerkleNode(node) for node in nodes]
        
        # Build the tree bottom-up
        while len(node_objects) > 1:
            next_level = []
            
            # Process pairs of nodes
            for i in range(0, len(node_objects), 2):
                left = node_objects[i]
                
                # If we have an odd number of nodes, duplicate the last one
                if i + 1 >= len(node_objects):
                    right = left
                else:
                    right = node_objects[i + 1]
                
                # Create a parent node with the hash of its children
                combined_hash = hashlib.sha256(left.hash + right.hash).digest()
                parent = MerkleNode(combined_hash, left, right)
                next_level.append(parent)
            
            node_objects = next_level
        
        # Return the root node
        return node_objects[0] if node_objects else None
    
    @property
    def root(self) -> bytes:
        """Get the root hash of the tree"""
        return self._root_hash if self._root_hash else b''

class FileChangeResult:
    """Container for file change results"""
    def __init__(self, changed_files: List[str], deleted_files: List[str]):
        self.changed_files = changed_files
        self.deleted_files = deleted_files
    
    def __repr__(self):
        return f"FileChangeResult(changed={len(self.changed_files)}, deleted={len(self.deleted_files)})"

class MerkleTreeService:
    def __init__(self):
        # Store previous merkle trees by codebase path
        self.previous_trees = {}
        self.previous_file_hashes = {}
    
    def build_merkle_tree(self, codebase_path: str) -> Tuple[MerkleTree, Dict[str, bytes]]:
        """
        Build a merkle tree from the codebase
        
        Args:
            codebase_path: Path to the codebase
            
        Returns:
            Tuple containing the merkle tree and a mapping of file paths to hashes
        """
        file_hashes = {}
        
        # Only include these file types
        include_extensions = [
            '.py',     # Python
            '.js',     # JavaScript
            '.jsx',    # React JSX
            '.ts',     # TypeScript
            '.tsx',    # TypeScript React
        ]
        
        # Explicitly exclude these file types (binary/media files)
        exclude_extensions = [
            '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.svg',  # Images
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', # Documents
            '.zip', '.tar', '.gz', '.rar', '.7z',  # Archives
            '.exe', '.dll', '.so', '.dylib',  # Binaries
            '.mp3', '.mp4', '.wav', '.avi', '.mov',  # Media
            '.ttf', '.otf', '.woff', '.woff2',  # Fonts
            '.pyc', '.pyo', '.pyd',  # Python bytecode
        ]
        
        # Directories to ignore
        ignore_dirs = [
            '.git',
            '.venv',
            'env',
            'venv',
            'node_modules',
            '__pycache__',
            '.idea',
            '.vscode',
            'dist',
            'build',
            '.pytest_cache',
            '.mypy_cache',
            'vendor',
            'tmp',
            '.dart_tool',
            'media',
            'static',
            'assets',
            'images',
        ]
        
        # Get all files in the codebase recursively
        for root, dirs, files in os.walk(codebase_path):
            # Skip entire directories - modify dirs in-place to avoid traversing
            dirs[:] = [d for d in dirs if not any(ignored == d or f"/{ignored}/" in f"/{d}/" 
                                                for ignored in ignore_dirs) 
                    and not d.startswith('.')]
            
            # Get relative path for filtering
            rel_path = os.path.relpath(root, codebase_path)
            
            # Special handling for root directory - don't skip it even if it's "."
            if rel_path == ".":
                # Process root directory normally
                pass
            # For non-root directories, apply ignore rules
            elif any(ignored in rel_path.split(os.path.sep) for ignored in ignore_dirs) or rel_path.startswith('.'):
                continue
                
            for file in files:
                # Skip files with excluded extensions
                if any(file.lower().endswith(ext) for ext in exclude_extensions):
                    continue
                    
                # Only include files with specified extensions
                if not any(file.lower().endswith(ext) for ext in include_extensions):
                    continue
                    
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, codebase_path)
                
                # Additional check for path components, but don't skip files at the root level
                if os.path.dirname(relative_path) and any(ignored in relative_path.split(os.path.sep) for ignored in ignore_dirs):
                    continue
                
                try:
                    # Use binary mode to avoid encoding issues
                    with open(file_path, 'rb') as f:
                        content = f.read()
                        # Calculate hash of the file content
                        file_hash = hashlib.sha256(content).digest()
                        # file_hash = calculate_hash(content)
                        file_hashes[relative_path] = file_hash
                except (IOError, OSError) as e:
                    # Skip files that cannot be read, with more specific error handling
                    continue
        
        # Create merkle tree from the file hashes
        hash_values = list(file_hashes.values())
        if not hash_values:
            hash_values = [b'empty']  # Add a default value if there are no files
            
        merkle_tree = MerkleTree(hash_values)
        
        return merkle_tree, file_hashes

    def get_changed_files(self, codebase_path: str) -> FileChangeResult:
        """
        Get changed and deleted files for a codebase path
        
        Args:
            codebase_path: Path to the codebase
            
        Returns:
            FileChangeResult containing changed files and deleted files
        """
        # Build new merkle tree
        new_tree, new_file_hashes = self.build_merkle_tree(codebase_path)
        
        # If no previous tree exists for this path, all files are considered changed
        if codebase_path not in self.previous_trees:
            self.previous_trees[codebase_path] = new_tree
            self.previous_file_hashes[codebase_path] = new_file_hashes
            return FileChangeResult(list(new_file_hashes.keys()), [])
        
        # Get previous tree and hashes
        old_tree = self.previous_trees[codebase_path]
        old_file_hashes = self.previous_file_hashes[codebase_path]
        
        # Compare trees and get changed/deleted files
        changed_files, deleted_files = self.compare_merkle_trees(
            old_tree, 
            new_tree, 
            old_file_hashes, 
            new_file_hashes
        )
        
        # Update stored trees and hashes
        self.previous_trees[codebase_path] = new_tree
        self.previous_file_hashes[codebase_path] = new_file_hashes
        
        return FileChangeResult(changed_files, deleted_files)
    
    def compare_merkle_trees(self, 
                             old_tree: MerkleTree, 
                             new_tree: MerkleTree, 
                             old_file_hashes: Dict[str, bytes], 
                             new_file_hashes: Dict[str, bytes]) -> Tuple[List[str], List[str]]:
        """
        Compare two merkle trees and return files that have changed and been deleted
        
        Args:
            old_tree: Previous merkle tree
            new_tree: Current merkle tree
            old_file_hashes: Previous file hashes mapping
            new_file_hashes: Current file hashes mapping
            
        Returns:
            Tuple containing (changed_files, deleted_files)
        """
        # Check if the root has changed
        if old_tree.root == new_tree.root:
            return [], []
            
        changed_files = []
        deleted_files = []
        
        # Find files that were added or modified
        for file_path, file_hash in new_file_hashes.items():
            if file_path not in old_file_hashes or old_file_hashes[file_path] != file_hash:
                changed_files.append(file_path)
                
        # Find files that were deleted
        for file_path in old_file_hashes:
            if file_path not in new_file_hashes:
                deleted_files.append(file_path)
                
        return changed_files, deleted_files

    def get_changed_files_legacy(self, codebase_path: str) -> List[str]:
        """
        Legacy method that returns only changed files (for backward compatibility)
        
        Args:
            codebase_path: Path to the codebase
            
        Returns:
            List of file paths that have changed (includes deleted files)
        """
        result = self.get_changed_files(codebase_path)
        # Combine changed and deleted files for backward compatibility
        return result.changed_files + result.deleted_files