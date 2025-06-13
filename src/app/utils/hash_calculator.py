import hashlib    
def calculate_special_hash(content) -> str:
    """
    Create a SHA-256 hash's special version of the given content (string or bytes).
    
    Args:
        content: The content to hash (string or bytes)
        
    Returns:
        The SHA-256 hash as a hexadecimal string with only 30 characters
    """
    if isinstance(content, str):
        content = content.encode('utf-8')
    return hashlib.sha256(content).hexdigest()[:30]

def calculate_hash(content) -> str:
    """
    Create a SHA-256 hash of the given content (string or bytes).
    
    Args:
        content: The content to hash (string or bytes)
        
    Returns:
        The SHA-256 hash as a hexadecimal string
    """
    if isinstance(content, str):
        content = content.encode('utf-8')
    return hashlib.sha256(content).hexdigest()