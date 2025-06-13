import hashlib
import os
from typing import Dict, List

from chonkie import CodeChunker, RecursiveChunker

from src.app.utils.logging_util import loggers


class CodeChunkingService:
    def __init__(self):
        # Initialize the CodeChunker with appropriate parameters
        self.lang_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".md": "markdown",
            ".txt": "text",
        }

        # Define which extensions should use text chunking vs code chunking
        self.text_extensions = {".md", ".txt"}

    def detect_language(self, file_path: str) -> str:
        """
        Detect the programming language based on file extension

        Args:
            file_path: Path to the file

        Returns:
            Language identifier string
        """
        ext = os.path.splitext(file_path)[1].lower()
        return self.lang_map.get(ext, "text")

    def is_text_file(self, file_path: str) -> bool:
        """
        Check if the file should be treated as text (markdown/txt) or code

        Args:
            file_path: Path to the file

        Returns:
            True if it's a text file, False if it's a code file
        """
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.text_extensions

    def determine_chunk_type(self, nodes: List[Dict], language: str) -> str:
        """
        Determine the chunk type based on AST nodes or language

        Args:
            nodes: List of AST nodes from chonkie (empty for text files)
            language: The detected language

        Returns:
            Chunk type as string
        """
        # For text-based files, always return "text"
        if language in ["markdown", "text"]:
            return "text"

        if not nodes:
            return "unknown"

        # Extract type information from the first node
        # This is a simplification - a more robust implementation would analyze the node structure
        node = nodes[0]
        if (
            isinstance(node, dict)
            and "tree" in node
            and "language" in node["tree"]
        ):
            types = node["tree"]["language"].get("types", [])

            # Check for specific types in the node
            type_map = {
                "function_definition": "function",
                "method_definition": "method",
                "class_definition": "class",
                "import_statement": "import",
                "variable_declaration": "variables",
            }

            for key, value in type_map.items():
                if key in types:
                    return value

        return "code"  # Default to generic code

    def calculate_line_numbers(
        self, content: str, start_index: int, end_index: int
    ) -> tuple:
        """
        Calculate start and end line numbers from character indices

        Args:
            content: File content
            start_index: Start character index
            end_index: End character index

        Returns:
            Tuple of (start_line, end_line)
        """
        lines = content.split("\n")
        start_line = 1
        current_pos = 0

        # Find start line
        for i, line in enumerate(lines):
            line_length = len(line) + 1  # +1 for the newline character
            if current_pos + line_length > start_index:
                start_line = i + 1
                break
            current_pos += line_length

        # Find end line
        end_line = start_line
        for i in range(start_line - 1, len(lines)):
            if current_pos > end_index:
                end_line = i + 1
                break
            current_pos += len(lines[i]) + 1
            end_line = i + 1

        return start_line, end_line

    def chunk_file(
        self, file_path: str, codebase_path: str, git_branch: str
    ) -> List[Dict]:
        """
        Chunk a single file and return chunks in the specified format

        Args:
            file_path: Path to the file
            codebase_path: Base path of the codebase
            git_branch: Current git branch

        Returns:
            List of chunk dictionaries
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            language = self.detect_language(file_path)

            if self.is_text_file(file_path):
                chunker = RecursiveChunker()
                chunks = chunker(content)
            else:
                chunker = CodeChunker(
                    language=language,
                    include_nodes=True,
                    tokenizer_or_token_counter="gpt2",
                )
                chunks = chunker(content)

            result_chunks = []
            for chunk in chunks:
                start_line, end_line = self.calculate_line_numbers(
                    content, chunk.start_index, chunk.end_index
                )

                # Calculate hash for the chunk content
                chunk_hash_string = (
                    f"{file_path}:{start_line}:{end_line}:{chunk.text}"
                )
                chunk_hash = hashlib.sha256(
                    chunk_hash_string.encode("utf-8")
                ).hexdigest()

                content_hash = hashlib.sha256(
                    chunk.text.encode("utf-8")
                ).hexdigest()

                # Determine chunk type - pass language for text files
                chunk_type = self.determine_chunk_type(
                    chunk.nodes if hasattr(chunk, "nodes") else [], language
                )

                # Relative file path from codebase
                relative_path = os.path.relpath(file_path, codebase_path)

                # Create chunk dictionary
                chunk_dict = {
                    "chunk_hash": chunk_hash,
                    "content_hash": content_hash,
                    "content": chunk.text,
                    "file_path": relative_path,
                    "start_line": start_line,
                    "end_line": end_line,
                    "language": language,
                    "chunk_type": chunk_type,
                    "git_branch": git_branch,
                    "token_count": chunk.token_count,
                }

                result_chunks.append(chunk_dict)

            return result_chunks
        except Exception as e:
            # Log error and continue
            loggers["main"].error(f"Error chunking file {file_path}: {str(e)}")
            return []
