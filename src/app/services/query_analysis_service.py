from typing import Dict, List, Any, Tuple

class QueryAnalysisService:
    """Service to analyze natural language queries and extract code entities and intent."""
    
    def __init__(self):
        self.entity_types = ["file", "function", "class", "method", "variable", "import", "directory"]
        self.intent_keywords = {
            "implement": "implementation",
            "code": "implementation",
            "how": "implementation",
            "function": "implementation",
            "works": "implementation",
            "what": "information",
            "where": "location",
            "who": "usage",
            "which": "information",
            "why": "explanation",
            "when": "usage",
            "find": "search",
            "search": "search",
            "list": "list",
            "show": "list",
            "display": "list",
            "uses": "usage",
            "calls": "usage",
            "imports": "dependency",
            "depends": "dependency",
            "inherits": "inheritance",
            "extends": "inheritance"
        }
        
    async def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze a natural language query to extract entities, intent, and constraints.
        
        Args:
            query: The natural language query string
            
        Returns:
            Dictionary containing extracted entities, intent, and constraints
        """
        query = query.lower()
        words = query.split()
        
        # Extract potential code entities (functions, classes, files, etc.)
        entities = self._extract_entities(query)
        
        # Determine query intent (what kind of information is being requested)
        intent = self._determine_intent(query)
        
        # Extract any constraints on the search
        constraints = self._extract_constraints(query)
        
        return {
            "raw_query": query,
            "entities": entities,
            "intent": intent,
            "constraints": constraints
        }
    
    def _extract_entities(self, query: str) -> Dict[str, List[str]]:
        """Extract code entities mentioned in the query."""
        words = query.split()
        entities = {entity_type: [] for entity_type in self.entity_types}
        
        # Basic entity extraction based on patterns
        # In a real implementation, this would use more sophisticated NLP techniques
        
        # Look for file references
        if "file" in query or "files" in query:
            # Find words that might be file names (contain extensions or are near "file" keyword)
            for word in words:
                if "." in word and word.split(".")[-1] in ["py", "js", "tsx", "jsx", "ts"]:
                    entities["file"].append(word)
        
        # Look for function references
        if "function" in query or "functions" in query or "method" in query or "methods" in query:
            # Look for words that might be function names (typically camelCase or snake_case)
            for i, word in enumerate(words):
                if i > 0 and (words[i-1] == "function" or words[i-1] == "method"):
                    # Strip punctuation
                    clean_word = word.strip(",.()[]{}\"'")
                    if clean_word and clean_word not in self.intent_keywords:
                        entities["function"].append(clean_word)
        
        # Look for class references
        if "class" in query or "classes" in query:
            for i, word in enumerate(words):
                if i > 0 and words[i-1] == "class":
                    # Strip punctuation
                    clean_word = word.strip(",.()[]{}\"'")
                    if clean_word and clean_word not in self.intent_keywords:
                        entities["class"].append(clean_word)
        
        return entities
    
    def _determine_intent(self, query: str) -> str:
        """Determine the intent of the query."""
        words = query.split()
        
        # Default intent
        intent = "information"
        
        # Check for specific intent keywords
        for word in words:
            clean_word = word.strip(",.?!;:")
            if clean_word in self.intent_keywords:
                intent = self.intent_keywords[clean_word]
                break
        
        # Look for specific query patterns
        if "how does" in query or "how do" in query:
            intent = "implementation"
        elif "where is" in query or "where are" in query:
            intent = "location"
        elif "who uses" in query or "what uses" in query:
            intent = "usage"
        elif "what is" in query or "what are" in query:
            intent = "information"
        
        return intent
    
    def _extract_constraints(self, query: str) -> Dict[str, Any]:
        """Extract constraints on the search (e.g., limit, file type)."""
        constraints = {}
        
        # Extract language constraints
        if "python" in query or ".py" in query:
            constraints["language"] = "python"
        elif "javascript" in query or "js" in query or ".js" in query:
            constraints["language"] = "javascript"
        elif "typescript" in query or "ts" in query or ".ts" in query:
            constraints["language"] = "typescript"
        
        # Extract quantity constraints
        if "all" in query:
            constraints["limit"] = None  # No limit
        
        return constraints 