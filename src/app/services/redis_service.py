import json
import pickle
from fastapi import Depends, HTTPException
import redis
from src.app.config.settings import settings

class RedisService:
    def __init__(self):
        self.redis_client = None
        self.connect()
        
    def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=False  # We need binary data for storing merkle trees
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Unable to connect to Redis: {str(e)}"
            )
            
    def get_client(self):
        """Get Redis client"""
        if not self.redis_client:
            self.connect()
        return self.redis_client
        
    def store_merkle_tree(self, key: str, merkle_tree, file_hashes):
        """
        Store merkle tree and file hashes in Redis
        
        Args:
            key: Redis key (git_branch:workspace_path)
            merkle_tree: MerkleTree object
            file_hashes: Dictionary of file paths to hashes
        """
        try:
            # Serialize the data
            data = {
                'merkle_tree': merkle_tree,
                'file_hashes': file_hashes
            }
            serialized_data = pickle.dumps(data)
            
            # Store in Redis
            self.redis_client.set(key, serialized_data)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error storing merkle tree in Redis: {str(e)}"
            )
            
    def get_merkle_tree(self, key: str):
        """
        Retrieve merkle tree and file hashes from Redis
        
        Args:
            key: Redis key (git_branch:workspace_path)
            
        Returns:
            Tuple of (merkle_tree, file_hashes) or None if not found
        """
        try:
            data = self.redis_client.get(key)
            if not data:
                return None
                
            # Deserialize the data
            deserialized_data = pickle.loads(data)
            return deserialized_data['merkle_tree'], deserialized_data['file_hashes']
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error retrieving merkle tree from Redis: {str(e)}"
            )