import os
import json
import pickle
import base64
from typing import Dict, Tuple, Any, Optional
from pathlib import Path
from fastapi import HTTPException

class FileStorageService:
    def __init__(self):
        # Create .cgcm directory at the root of the project
        self.base_dir = Path('.') / ".cgcm"
        self.base_dir.mkdir(exist_ok=True)
    
    def _get_workspace_dir(self, workspace_path: str) -> Path:
        """Create and get directory for the workspace within .cgcm"""
        # Get just the basename of the workspace path
        workspace_name = os.path.basename(workspace_path.rstrip('/'))
        if not workspace_name:  # Handle cases like "/" or where path ends with "/"
            workspace_name = 'root'
            
        # Create directory for this workspace
        workspace_dir = self.base_dir / workspace_name
        workspace_dir.mkdir(exist_ok=True)
        return workspace_dir
    
    def _serialize_data(self, data: Dict) -> Dict:
        """Serialize data to be JSON compatible"""
        serialized = {}
        
        # Serialize merkle tree using pickle and convert to base64 string
        serialized['merkle_tree'] = base64.b64encode(pickle.dumps(data['merkle_tree'])).decode('utf-8')
        
        # Serialize file_hashes - convert bytes to base64 strings
        serialized['file_hashes'] = {}
        for file_path, file_hash in data['file_hashes'].items():
            serialized['file_hashes'][file_path] = base64.b64encode(file_hash).decode('utf-8')
            
        return serialized
    
    def _deserialize_data(self, data: Dict) -> Dict:
        """Deserialize data from JSON compatible format"""
        deserialized = {}
        
        # Deserialize merkle tree from base64 string
        deserialized['merkle_tree'] = pickle.loads(base64.b64decode(data['merkle_tree']))
        
        # Deserialize file_hashes - convert base64 strings back to bytes
        deserialized['file_hashes'] = {}
        for file_path, file_hash_b64 in data['file_hashes'].items():
            deserialized['file_hashes'][file_path] = base64.b64decode(file_hash_b64)
            
        return deserialized
    
    def store_merkle_tree(self, key: str, merkle_tree, file_hashes):
        """
        Store merkle tree and file hashes in a JSON file
        
        Args:
            key: Storage key (git_branch:workspace_path)
            merkle_tree: MerkleTree object
            file_hashes: Dictionary of file paths to hashes
        """
        try:
            # Extract workspace path and git branch from key
            parts = key.split(':')
            if len(parts) != 2:
                raise ValueError(f"Invalid key format: {key}")
                
            workspace_path, git_branch = parts
            
            # Get just the basename for the key
            workspace_basename = os.path.basename(workspace_path.rstrip('/'))
            
            # Create the storage key in the format workspace_basename_git_branch_name
            storage_key = f"{workspace_basename}_{git_branch}"
            
            # Get workspace directory
            workspace_dir = self._get_workspace_dir(workspace_path)
            
            # Create file path for storing merkle tree data
            file_path = workspace_dir / "merkle_tree.json"
            
            # Read existing data if file exists
            data = {}
            if file_path.exists():
                with open(file_path, 'r') as f:
                    data = json.load(f)
            
            # Prepare data for storage
            tree_data = {
                'merkle_tree': merkle_tree,
                'file_hashes': file_hashes
            }
            
            # Serialize for JSON storage
            serialized_data = self._serialize_data(tree_data)
            
            # Store under the combined key
            data[storage_key] = serialized_data
            
            # Write to file
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error storing merkle tree in file: {str(e)}"
            )
            
    def get_merkle_tree(self, key: str) -> Optional[Tuple[Any, Dict]]:
        """
        Retrieve merkle tree and file hashes from file storage
        
        Args:
            key: Storage key (git_branch:workspace_path)
            
        Returns:
            Tuple of (merkle_tree, file_hashes) or None if not found
        """
        try:
            # Extract workspace path and git branch from key
            parts = key.split(':')
            if len(parts) != 2:
                raise ValueError(f"Invalid key format: {key}")
                
            workspace_path, git_branch = parts
            
            # Get just the basename for the key
            workspace_basename = os.path.basename(workspace_path.rstrip('/'))
            
            # Create the storage key in the format workspace_basename_git_branch_name
            storage_key = f"{workspace_basename}_{git_branch}"
            
            # Get workspace directory
            workspace_dir = self._get_workspace_dir(workspace_path)
            
            # Create file path for retrieving merkle tree data
            file_path = workspace_dir / "merkle_tree.json"
            
            # Check if file exists
            if not file_path.exists():
                return None
                
            # Read data from file
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Check if storage key exists in data
            if storage_key not in data:
                return None
                
            # Get data for the specified key
            key_data = data[storage_key]
            
            # Deserialize data
            deserialized_data = self._deserialize_data(key_data)
            
            return deserialized_data['merkle_tree'], deserialized_data['file_hashes']
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error retrieving merkle tree from file: {str(e)}"
            )
        
    async def store_in_file_storage(self, key: str, insights: Dict | str, file_name: str):
        """
        Store natural language insights in a JSON file
        """
        try:
            # Extract workspace path and git branch from key
            parts = key.split(':')
            if len(parts) != 2:
                raise ValueError(f"Invalid key format: {key}")
                
            workspace_path, git_branch = parts
            
            workspace_basename = os.path.basename(workspace_path.rstrip('/'))
            storage_key = f"{workspace_basename}_{git_branch}"
            workspace_dir = self._get_workspace_dir(workspace_path)
            file_path = workspace_dir / f"{file_name}"
            
            data = {}
            if file_path.exists():
                with open(file_path, 'r') as f:
                    data = json.load(f)

            data[storage_key] = insights

            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error storing merkle tree in file: {str(e)}"
            )
        
    async def get_from_file_storage(self, key: str, file_name: str) -> Optional[Tuple[Any, Dict]]:
        """
        Retrieve merkle tree and file hashes from file storage
        
        Args:
            key: Storage key (git_branch:workspace_path)
            
        Returns:
            Tuple of (merkle_tree, file_hashes) or None if not found
        """
        try:
            # Extract workspace path and git branch from key
            parts = key.split(':')
            if len(parts) != 2:
                raise ValueError(f"Invalid key format: {key}")
                
            workspace_path, git_branch = parts
            workspace_basename = os.path.basename(workspace_path.rstrip('/'))
            storage_key = f"{workspace_basename}_{git_branch}"

            workspace_dir = self._get_workspace_dir(workspace_path)

            file_path = workspace_dir / f"{file_name}"

            if not file_path.exists():
                return None

            with open(file_path, 'r') as f:
                data = json.load(f)

            if storage_key not in data:
                return None

            key_data = data[storage_key]
            
            return key_data
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error retrieving merkle tree from file: {str(e)}"
            )
        
    async def store_variable_in_file_storage(self, data: Dict, file_name: str, workspace_path: str):
        """
        Store variable in a JSON file
        """
        try:
            workspace_dir = self._get_workspace_dir(workspace_path)
            file_path = workspace_dir / f"{file_name}"
            
            # Always overwrite the file with new content
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error storing variable in file: {str(e)}"
            )
        
    async def get_variable_from_file_storage(self, file_name: str, workspace_path: str) -> Optional[Dict]:
        """
        Retrieve variable from a JSON file
        """
        try:
            workspace_dir = self._get_workspace_dir(workspace_path)
            file_path = workspace_dir / f"{file_name}"
            
            if not file_path.exists():  
                return None
            
            with open(file_path, 'r') as f:
                data = json.load(f)

            return data
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error retrieving variable from file: {str(e)}"
            )