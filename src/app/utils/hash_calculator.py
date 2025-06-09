import hashlib    
def calculate_special_hash(content: str) -> str:
    """
    Create a SHA-256 hash's special version of the given string content.
    
    Args:
        content: The string content to hash
        
    Returns:
        The SHA-256 hash as a hexadecimal string with only 30 characters
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:30]

def calculate_hash(content: str) -> str:
    """
    Create a SHA-256 hash of the given string content.
    
    Args:
        content: The string content to hash
        
    Returns:
        The SHA-256 hash as a hexadecimal string
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()