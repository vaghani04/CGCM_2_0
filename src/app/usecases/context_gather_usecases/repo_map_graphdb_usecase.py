from typing import Dict, Any

from src.app.services.repo_map_service import RepositoryMapService
from src.app.services.neo4j_service import Neo4jService
from src.app.services.graphdb_import_service import GraphDBImportService


class RepoMapGraphDBUseCase:
    """UseCase for generating repository maps and storing them in GraphDB."""
    
    def __init__(self):
        self.repo_map_service = RepositoryMapService()
        self.neo4j_service = Neo4jService()
        self.graphdb_import_service = GraphDBImportService(self.neo4j_service)
    
    async def generate_and_store_repo_map(self, codebase_path: str, 
                                        output_file: str = None) -> Dict[str, Any]:
        """
        Generate repository map and store it in GraphDB.
        IMPORTANT: This method clears the entire GraphDB before storing the new repo map.
        
        Args:
            codebase_path: Path to the codebase to analyze
            output_file: Optional output file for JSON backup
            
        Returns:
            Dictionary with generation and import statistics
        """
        
        try:
            # Step 1: Clear GraphDB before generating new repo map
            print("🧹 Clearing GraphDB before generating new repo map...")
            clear_result = await self.clear_graphdb()
            if clear_result["status"] != "success":
                print(f"⚠️ Warning: Failed to clear GraphDB: {clear_result.get('error_message', 'Unknown error')}")
            else:
                print("✓ GraphDB cleared successfully")
            
            # Step 2: Generate repository map
            print("🔍 Generating repository map...")
            repo_map_result = await self.repo_map_service.generate_repository_map(
                codebase_path=codebase_path,
                output_file=output_file
            )
            
            print(f"✓ Repository map generated successfully")
            repo_map_data = repo_map_result["repo_map_data"]
            
            # Step 3: Import into GraphDB
            print("📊 Importing repository map into GraphDB...")
            import_stats = await self.graphdb_import_service.import_repository_map(repo_map_data)
            
            # Step 4: Get database statistics
            db_stats = await self.graphdb_import_service.get_import_stats()
            
            # Combine results
            result = {
                "status": "success",
                "repository_map_generation": repo_map_result,
                "graphdb_import": import_stats,
                "graphdb_statistics": db_stats,
                "summary": {
                    "total_files_processed": repo_map_result['total_files_analyzed'],
                    "processing_time_seconds": repo_map_result['processing_time_seconds'],
                    "nodes_created": (
                        import_stats['directories_created'] + 
                        import_stats['files_created'] + 
                        import_stats['functions_created'] + 
                        import_stats['classes_created'] + 
                        import_stats['imports_created']
                    ),
                    "relationships_created": import_stats['relationships_created'],
                    "errors": import_stats.get('errors', [])
                }
            }
            
            print("✅ Repository map generation and GraphDB import completed successfully!")
            return result
            
        except Exception as e:
            error_result = {
                "status": "error",
                "error_message": str(e),
                "error_type": type(e).__name__
            }
            print(f"❌ Repository map generation/import failed: {e}")
            return error_result
    
    async def get_graphdb_statistics(self) -> Dict[str, Any]:
        """Get current GraphDB statistics."""
        try:
            stats = await self.neo4j_service.get_database_stats()
            return {
                "status": "success",
                "statistics": stats
            }
        except Exception as e:
            return {
                "status": "error",
                "error_message": str(e)
            }
    
    async def clear_graphdb(self) -> Dict[str, Any]:
        """Clear all data from GraphDB."""
        try:
            success = await self.neo4j_service.clear_database()
            return {
                "status": "success" if success else "error",
                "message": "GraphDB cleared successfully" if success else "Failed to clear GraphDB"
            }
        except Exception as e:
            return {
                "status": "error",
                "error_message": str(e)
            }
    
    async def check_graphdb_connection(self) -> Dict[str, Any]:
        """Check GraphDB connection status."""
        try:
            is_connected = self.neo4j_service.is_connected()
            return {
                "status": "success",
                "connected": is_connected,
                "message": "GraphDB connection is active" if is_connected else "GraphDB connection is not available"
            }
        except Exception as e:
            return {
                "status": "error",
                "connected": False,
                "error_message": str(e)
            }
    
    def close_connections(self):
        """Close all database connections."""
        if self.neo4j_service:
            self.neo4j_service.close() 