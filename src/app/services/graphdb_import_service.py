import json
import os
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

from src.app.services.neo4j_service import Neo4jService
from src.app.models.domain.graphdb_models import (
    FileNode, DirectoryNode, FunctionNode, ClassNode, ImportNode,
    GraphRelationship, GraphIndexRequest, GraphConstraintRequest,
    NodeType, RelationshipType
)
from src.app.models.domain.repo_map_models import RepositoryMap


class GraphDBImportService:
    """Service for importing repository map data into GraphDB."""
    
    def __init__(self, neo4j_service: Neo4jService):
        self.neo4j_service = neo4j_service
        self.node_id_cache: Dict[str, str] = {}  # Cache for node IDs
        
    async def import_repository_map(self, repo_map_data: Dict) -> Dict[str, Any]:
        """Import complete repository map into GraphDB."""
        
        print("Starting GraphDB import process...")
        
        # Clear existing data if needed
        await self.neo4j_service.clear_database()
        print("✓ Cleared existing data")
        
        # Create indexes and constraints first
        await self._setup_database_schema()
        print("✓ Database schema setup complete")
        
        # Parse repository map
        if isinstance(repo_map_data, dict):
            repo_map = repo_map_data
        else:
            repo_map = repo_map_data
        
        import_stats = {
            "directories_created": 0,
            "files_created": 0,
            "functions_created": 0,
            "classes_created": 0,
            "imports_created": 0,
            "relationships_created": 0,
            "errors": []
        }
        
        try:
            # Step 1: Create directory structure
            await self._create_directory_structure(repo_map, import_stats)
            print(f"✓ Created {import_stats['directories_created']} directories")
            
            # Step 2: Create file nodes
            await self._create_file_nodes(repo_map, import_stats)
            print(f"✓ Created {import_stats['files_created']} files")
            
            # Step 3: Create function and class nodes
            await self._create_code_entities(repo_map, import_stats)
            print(f"✓ Created {import_stats['functions_created']} functions and {import_stats['classes_created']} classes")
            
            # Step 4: Create import nodes and relationships
            await self._create_import_relationships(repo_map, import_stats)
            print(f"✓ Created {import_stats['imports_created']} imports")
            
            # Step 5: Create dependency relationships
            await self._create_dependency_relationships(repo_map, import_stats)
            print(f"✓ Created dependency relationships")
            
            print("✓ GraphDB import completed successfully")
            
        except Exception as e:
            error_msg = f"GraphDB import failed: {e}"
            import_stats["errors"].append(error_msg)
            print(f"✗ {error_msg}")
            raise
        
        return import_stats
    
    async def _setup_database_schema(self):
        """Create indexes and constraints for optimal performance."""
        
        # Define indexes for common queries
        indexes = [
            GraphIndexRequest(NodeType.FILE, "path"),
            GraphIndexRequest(NodeType.FILE, "language"),
            GraphIndexRequest(NodeType.DIRECTORY, "path"),
            GraphIndexRequest(NodeType.FUNCTION, "name"),
            GraphIndexRequest(NodeType.FUNCTION, "file_path"),
            GraphIndexRequest(NodeType.CLASS, "name"),
            GraphIndexRequest(NodeType.CLASS, "file_path"),
            GraphIndexRequest(NodeType.IMPORT, "module"),
        ]
        
        # Define constraints for data integrity
        constraints = [
            GraphConstraintRequest(NodeType.FILE, ["path"]),
            GraphConstraintRequest(NodeType.DIRECTORY, ["path"]),
            GraphConstraintRequest(NodeType.FUNCTION, ["name", "file_path", "line_number"]),
            GraphConstraintRequest(NodeType.CLASS, ["name", "file_path", "line_number"]),
        ]
        
        # Create indexes
        await self.neo4j_service.create_indexes(indexes)
        
        # Create constraints
        await self.neo4j_service.create_constraints(constraints)
    
    async def _create_directory_structure(self, repo_map: Dict, stats: Dict):
        """Create directory nodes and relationships."""
        
        root_path = repo_map.get("root_path", "")
        directory_structure = repo_map.get("directory_structure", {})
        
        # Create root directory
        root_node = DirectoryNode(
            path=root_path,
            name=os.path.basename(root_path) or "root"
        )
        
        root_id = await self.neo4j_service.create_node(root_node)
        self.node_id_cache[root_path] = root_id
        stats["directories_created"] += 1
        
        # Recursively create directory structure
        await self._create_directory_nodes_recursive(
            directory_structure, root_path, root_id, stats
        )
    
    async def _create_directory_nodes_recursive(self, structure: Dict, parent_path: str, 
                                              parent_id: str, stats: Dict):
        """Recursively create directory nodes."""
        
        for name, content in structure.items():
            if isinstance(content, dict):
                if content.get("type") == "file":
                    # Skip files for now, they'll be handled later
                    continue
                else:
                    # It's a directory
                    dir_path = os.path.join(parent_path, name)
                    dir_node = DirectoryNode(path=dir_path, name=name)
                    
                    dir_id = await self.neo4j_service.create_node(dir_node)
                    self.node_id_cache[dir_path] = dir_id
                    stats["directories_created"] += 1
                    
                    # Create CONTAINS relationship
                    relationship = GraphRelationship(
                        relationship_type=RelationshipType.CONTAINS,
                        from_node_id=parent_id,
                        to_node_id=dir_id
                    )
                    await self.neo4j_service.create_relationship(relationship)
                    stats["relationships_created"] += 1
                    
                    # Recurse into subdirectory
                    await self._create_directory_nodes_recursive(
                        content, dir_path, dir_id, stats
                    )
    
    async def _create_file_nodes(self, repo_map: Dict, stats: Dict):
        """Create file nodes and connect them to directories."""
        
        files = repo_map.get("files", [])
        file_nodes = []
        
        for file_info in files:
            file_node = FileNode(
                path=file_info["path"],
                language=file_info["language"],
                lines_of_code=file_info["lines_of_code"],
                docstring=file_info.get("docstring")
            )
            file_nodes.append(file_node)
        
        # Batch create file nodes
        file_ids = await self.neo4j_service.batch_create_nodes(file_nodes)
        
        # Cache file node IDs
        for file_info, file_id in zip(files, file_ids):
            if file_id:
                self.node_id_cache[file_info["path"]] = file_id
                stats["files_created"] += 1
        
        # Create directory-file relationships
        await self._create_file_directory_relationships(files, stats)
    
    async def _create_file_directory_relationships(self, files: List[Dict], stats: Dict):
        """Create relationships between directories and files."""
        
        relationships = []
        
        for file_info in files:
            file_path = file_info["path"]
            file_id = self.node_id_cache.get(file_path)
            
            if not file_id:
                continue
            
            # Find parent directory
            parent_dir = os.path.dirname(file_path)
            parent_id = self.node_id_cache.get(parent_dir)
            
            if parent_id:
                relationship = GraphRelationship(
                    relationship_type=RelationshipType.CONTAINS,
                    from_node_id=parent_id,
                    to_node_id=file_id
                )
                relationships.append(relationship)
        
        # Batch create relationships
        results = await self.neo4j_service.batch_create_relationships(relationships)
        stats["relationships_created"] += sum(results)
    
    async def _create_code_entities(self, repo_map: Dict, stats: Dict):
        """Create function and class nodes."""
        
        files = repo_map.get("files", [])
        function_nodes = []
        class_nodes = []
        method_relationships = []
        
        for file_info in files:
            file_path = file_info["path"]
            file_id = self.node_id_cache.get(file_path)
            
            if not file_id:
                continue
            
            # Create function nodes
            for func_info in file_info.get("functions", []):
                func_node = FunctionNode(
                    name=func_info["name"],
                    file_path=file_path,
                    line_number=func_info["line_number"],
                    parameters=func_info.get("parameters", []),
                    return_type=func_info.get("return_type"),
                    docstring=func_info.get("docstring"),
                    visibility=func_info.get("visibility", "public"),
                    is_async=func_info.get("is_async", False),
                    is_method=func_info.get("is_method", False)
                )
                function_nodes.append(func_node)
            
            # Create class nodes
            for class_info in file_info.get("classes", []):
                class_node = ClassNode(
                    name=class_info["name"],
                    file_path=file_path,
                    line_number=class_info["line_number"],
                    bases=class_info.get("bases", []),
                    docstring=class_info.get("docstring"),
                    method_count=len(class_info.get("methods", [])),
                    attribute_count=len(class_info.get("attributes", []))
                )
                class_nodes.append(class_node)
        
        # Batch create nodes
        function_ids = await self.neo4j_service.batch_create_nodes(function_nodes)
        class_ids = await self.neo4j_service.batch_create_nodes(class_nodes)
        
        stats["functions_created"] = len([id for id in function_ids if id])
        stats["classes_created"] = len([id for id in class_ids if id])
        
        # Create file-function and file-class relationships
        await self._create_code_entity_relationships(
            repo_map, function_nodes, function_ids, class_nodes, class_ids, stats
        )
    
    async def _create_code_entity_relationships(self, repo_map: Dict, 
                                              function_nodes: List, function_ids: List,
                                              class_nodes: List, class_ids: List, stats: Dict):
        """Create relationships for functions and classes."""
        
        relationships = []
        
        # File-Function relationships
        for func_node, func_id in zip(function_nodes, function_ids):
            if not func_id:
                continue
                
            file_id = self.node_id_cache.get(func_node.properties["file_path"])
            if file_id:
                relationship = GraphRelationship(
                    relationship_type=RelationshipType.CONTAINS,
                    from_node_id=file_id,
                    to_node_id=func_id
                )
                relationships.append(relationship)
        
        # File-Class relationships
        for class_node, class_id in zip(class_nodes, class_ids):
            if not class_id:
                continue
                
            file_id = self.node_id_cache.get(class_node.properties["file_path"])
            if file_id:
                relationship = GraphRelationship(
                    relationship_type=RelationshipType.CONTAINS,
                    from_node_id=file_id,
                    to_node_id=class_id
                )
                relationships.append(relationship)
        
        # Create class method relationships
        await self._create_class_method_relationships(repo_map, class_nodes, class_ids, relationships, stats)
        
        # Batch create all relationships
        results = await self.neo4j_service.batch_create_relationships(relationships)
        stats["relationships_created"] += sum(results)
    
    async def _create_class_method_relationships(self, repo_map: Dict, class_nodes: List, 
                                               class_ids: List, relationships: List, stats: Dict):
        """Create relationships between classes and their methods."""
        
        files = repo_map.get("files", [])
        
        # Create a mapping of class name + file to class ID
        class_map = {}
        for class_node, class_id in zip(class_nodes, class_ids):
            if class_id:
                key = f"{class_node.properties['name']}:{class_node.properties['file_path']}"
                class_map[key] = class_id
        
        # Create method nodes and relationships
        method_nodes = []
        for file_info in files:
            file_path = file_info["path"]
            
            for class_info in file_info.get("classes", []):
                class_key = f"{class_info['name']}:{file_path}"
                class_id = class_map.get(class_key)
                
                if not class_id:
                    continue
                
                for method_info in class_info.get("methods", []):
                    method_node = FunctionNode(
                        name=method_info["name"],
                        file_path=file_path,
                        line_number=method_info["line_number"],
                        parameters=method_info.get("parameters", []),
                        return_type=method_info.get("return_type"),
                        docstring=method_info.get("docstring"),
                        visibility=method_info.get("visibility", "public"),
                        is_async=method_info.get("is_async", False),
                        is_method=True
                    )
                    method_nodes.append((method_node, class_id))
        
        # Batch create method nodes
        if method_nodes:
            nodes_only = [node for node, _ in method_nodes]
            method_ids = await self.neo4j_service.batch_create_nodes(nodes_only)
            
            # Create class-method relationships
            for (method_node, class_id), method_id in zip(method_nodes, method_ids):
                if method_id:
                    relationship = GraphRelationship(
                        relationship_type=RelationshipType.DEFINES,
                        from_node_id=class_id,
                        to_node_id=method_id
                    )
                    relationships.append(relationship)
    
    async def _create_import_relationships(self, repo_map: Dict, stats: Dict):
        """Create import nodes and relationships."""
        
        files = repo_map.get("files", [])
        import_nodes = []
        import_relationships = []
        
        for file_info in files:
            file_path = file_info["path"]
            file_id = self.node_id_cache.get(file_path)
            
            if not file_id:
                continue
            
            for import_info in file_info.get("imports", []):
                import_node = ImportNode(
                    module=import_info["module"],
                    names=import_info.get("names", []),
                    alias=import_info.get("alias"),
                    is_from_import=import_info.get("is_from_import", False),
                    file_path=file_path
                )
                import_nodes.append((import_node, file_id))
        
        # Batch create import nodes
        if import_nodes:
            nodes_only = [node for node, _ in import_nodes]
            import_ids = await self.neo4j_service.batch_create_nodes(nodes_only)
            
            # Create file-import relationships
            relationships = []
            for (import_node, file_id), import_id in zip(import_nodes, import_ids):
                if import_id:
                    relationship = GraphRelationship(
                        relationship_type=RelationshipType.IMPORTS,
                        from_node_id=file_id,
                        to_node_id=import_id
                    )
                    relationships.append(relationship)
            
            results = await self.neo4j_service.batch_create_relationships(relationships)
            stats["imports_created"] = len([id for id in import_ids if id])
            stats["relationships_created"] += sum(results)
    
    async def _create_dependency_relationships(self, repo_map: Dict, stats: Dict):
        """Create dependency relationships between files."""
        
        dependency_graph = repo_map.get("dependency_graph", {})
        relationships = []
        
        for from_file, to_files in dependency_graph.items():
            from_id = self.node_id_cache.get(from_file)
            if not from_id:
                continue
            
            for to_file in to_files:
                to_id = self.node_id_cache.get(to_file)
                if to_id:
                    relationship = GraphRelationship(
                        relationship_type=RelationshipType.DEPENDS_ON,
                        from_node_id=from_id,
                        to_node_id=to_id
                    )
                    relationships.append(relationship)
        
        # Batch create dependency relationships
        if relationships:
            results = await self.neo4j_service.batch_create_relationships(relationships)
            stats["relationships_created"] += sum(results)
    
    async def get_import_stats(self) -> Dict[str, Any]:
        """Get statistics about the imported data."""
        return await self.neo4j_service.get_database_stats() 