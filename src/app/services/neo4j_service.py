import json
import time
from typing import Dict, List, Optional, Any, Union
from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import ServiceUnavailable, TransientError

from src.app.config.settings import settings
from src.app.models.domain.graphdb_models import (
    GraphNode, GraphRelationship, GraphQuery, GraphQueryResult,
    BatchOperation, GraphIndexRequest, GraphConstraintRequest,
    NodeType, RelationshipType
)


class Neo4jService:
    """Service for Neo4j graph database operations."""
    
    def __init__(self):
        self.driver: Optional[Driver] = None
        self._connect()
    
    def _connect(self):
        """Establish connection to Neo4j database."""
        try:
            self.driver = GraphDatabase.driver(
                settings.NEO4J_URI,
              auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            # Test the connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            print("✓ Connected to Neo4j database")
        except Exception as e:
            print(f"✗ Failed to connect to Neo4j: {e}")
            self.driver = None
    
    def close(self):
        """Close the database connection."""
        if self.driver:
            self.driver.close()
    
    def is_connected(self) -> bool:
        """Check if the database connection is active."""
        if not self.driver:
            return False
        try:
            with self.driver.session() as session:
                session.run("RETURN 1")
            return True
        except:
            return False
    
    async def execute_query(self, query: GraphQuery) -> GraphQueryResult:
        """Execute a Cypher query and return results."""
        if not self.driver:
            raise Exception("Neo4j driver not connected")
        
        try:
            with self.driver.session() as session:
                result = session.run(query.cypher_query, query.parameters)
                records = [record.data() for record in result]
                summary = {
                    "query": query.cypher_query,
                    "parameters": query.parameters,
                    "records_count": len(records)
                }
                return GraphQueryResult(records=records, summary=summary)
        except Exception as e:
            raise Exception(f"Query execution failed: {e}")
    
    async def create_node(self, node: GraphNode) -> str:
        """Create a single node in the graph database."""
        labels = ":".join(node.labels)
        
        # Convert properties to a format suitable for Cypher
        props_str = ", ".join([f"{k}: ${k}" for k in node.properties.keys()])
        
        query = GraphQuery(
            cypher_query=f"""
            CREATE (n:{labels} {{{props_str}}})
            RETURN id(n) as node_id
            """,
            parameters=node.properties
        )
        
        result = await self.execute_query(query)
        if result.records:
            return result.records[0]["node_id"]
        raise Exception("Failed to create node")
    
    async def create_relationship(self, relationship: GraphRelationship) -> bool:
        """Create a relationship between two nodes."""
        props_str = ""
        if relationship.properties:
            props_str = "{" + ", ".join([f"{k}: ${k}" for k in relationship.properties.keys()]) + "}"
        
        query = GraphQuery(
            cypher_query=f"""
            MATCH (a), (b)
            WHERE id(a) = $from_id AND id(b) = $to_id
            CREATE (a)-[r:{relationship.relationship_type.value} {props_str}]->(b)
            RETURN id(r) as rel_id
            """,
            parameters={
                "from_id": relationship.from_node_id,
                "to_id": relationship.to_node_id,
                **(relationship.properties or {})
            }
        )
        
        result = await self.execute_query(query)
        return len(result.records) > 0
    
    async def batch_create_nodes(self, nodes: List[GraphNode]) -> List[str]:
        """Create multiple nodes in batch."""
        if not nodes:
            return []
        
        node_ids = []
        batch_size = settings.GRAPHDB_BATCH_SIZE
        
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i + batch_size]
            batch_ids = await self._create_node_batch(batch)
            node_ids.extend(batch_ids)
        
        return node_ids
    
    async def _create_node_batch(self, nodes: List[GraphNode]) -> List[str]:
        """Create a batch of nodes."""
        if not self.driver:
            raise Exception("Neo4j driver not connected")
        
        with self.driver.session() as session:
            # Prepare batch data
            batch_data = []
            for i, node in enumerate(nodes):
                labels = ":".join(node.labels)
                batch_data.append({
                    "index": i,
                    "labels": labels,
                    "properties": node.properties
                })
            
            query = """
            UNWIND $batch_data as item
            CALL {
                WITH item
                CALL apoc.create.node(split(item.labels, ':'), item.properties) YIELD node
                RETURN id(node) as node_id, item.index as idx
            }
            RETURN node_id, idx
            ORDER BY idx
            """
            
            try:
                result = session.run(query, {"batch_data": batch_data})
                return [record["node_id"] for record in result]
            except Exception as e:
                # Fallback to individual creation if APOC is not available
                return await self._create_nodes_individually(nodes)
    
    async def _create_nodes_individually(self, nodes: List[GraphNode]) -> List[str]:
        """Fallback method to create nodes individually."""
        node_ids = []
        for node in nodes:
            try:
                node_id = await self.create_node(node)
                node_ids.append(node_id)
            except Exception as e:
                print(f"Failed to create node: {e}")
                node_ids.append(None)
        return node_ids
    
    async def batch_create_relationships(self, relationships: List[GraphRelationship]) -> List[bool]:
        """Create multiple relationships in batch."""
        if not relationships:
            return []
        
        results = []
        batch_size = settings.GRAPHDB_BATCH_SIZE
        
        for i in range(0, len(relationships), batch_size):
            batch = relationships[i:i + batch_size]
            batch_results = await self._create_relationship_batch(batch)
            results.extend(batch_results)
        
        return results
    
    async def _create_relationship_batch(self, relationships: List[GraphRelationship]) -> List[bool]:
        """Create a batch of relationships."""
        if not self.driver:
            raise Exception("Neo4j driver not connected")
        
        with self.driver.session() as session:
            batch_data = []
            for rel in relationships:
                batch_data.append({
                    "from_id": rel.from_node_id,
                    "to_id": rel.to_node_id,
                    "rel_type": rel.relationship_type.value,
                    "properties": rel.properties or {}
                })
            
            query = """
            UNWIND $batch_data as item
            MATCH (a), (b)
            WHERE id(a) = item.from_id AND id(b) = item.to_id
            CALL apoc.create.relationship(a, item.rel_type, item.properties, b) YIELD rel
            RETURN id(rel) as rel_id
            """
            
            try:
                result = session.run(query, {"batch_data": batch_data})
                return [True for _ in result]
            except Exception as e:
                # Fallback to individual creation
                return await self._create_relationships_individually(relationships)
    
    async def _create_relationships_individually(self, relationships: List[GraphRelationship]) -> List[bool]:
        """Fallback method to create relationships individually."""
        results = []
        for rel in relationships:
            try:
                success = await self.create_relationship(rel)
                results.append(success)
            except Exception as e:
                print(f"Failed to create relationship: {e}")
                results.append(False)
        return results
    
    async def clear_database(self) -> bool:
        """Clear all nodes and relationships from the database."""
        query = GraphQuery(
            cypher_query="MATCH (n) DETACH DELETE n"
        )
        
        try:
            await self.execute_query(query)
            return True
        except Exception as e:
            print(f"Failed to clear database: {e}")
            return False
    
    async def create_indexes(self, indexes: List[GraphIndexRequest]) -> List[bool]:
        """Create indexes for better query performance."""
        results = []
        
        for index_req in indexes:
            try:
                query = GraphQuery(
                    cypher_query=f"""
                    CREATE INDEX {index_req.node_type.value.lower()}_{index_req.property_name}_idx
                    IF NOT EXISTS
                    FOR (n:{index_req.node_type.value})
                    ON (n.{index_req.property_name})
                    """
                )
                await self.execute_query(query)
                results.append(True)
            except Exception as e:
                print(f"Failed to create index: {e}")
                results.append(False)
        
        return results
    
    async def create_constraints(self, constraints: List[GraphConstraintRequest]) -> List[bool]:
        """Create constraints for data integrity."""
        results = []
        
        for constraint_req in constraints:
            try:
                if constraint_req.constraint_type == "UNIQUE":
                    # First check for existing indexes that might conflict
                    for prop in constraint_req.property_names:
                        try:
                            # Drop any existing index for this property
                            drop_index_query = GraphQuery(
                                cypher_query=f"""
                                CALL db.indexes() YIELD name, labelsOrTypes, properties
                                WHERE labelsOrTypes[0] = '{constraint_req.node_type.value}' 
                                AND '{prop}' IN properties
                                RETURN name
                                """
                            )
                            
                            index_result = await self.execute_query(drop_index_query)
                            for record in index_result.records:
                                index_name = record.get("name")
                                if index_name:
                                    try:
                                        await self.execute_query(GraphQuery(
                                            cypher_query=f"DROP INDEX {index_name}"
                                        ))
                                        print(f"Dropped existing index: {index_name}")
                                    except Exception as drop_err:
                                        print(f"Error dropping index {index_name}: {drop_err}")
                        except Exception as idx_err:
                            print(f"Error checking indexes: {idx_err}")
                    
                    # Now create the constraint
                    properties = ", ".join([f"n.{prop}" for prop in constraint_req.property_names])
                    constraint_name = f"{constraint_req.node_type.value.lower()}_{'_'.join(constraint_req.property_names)}_unique"
                    
                    # For Neo4j 4.x compatibility
                    query = GraphQuery(
                        cypher_query=f"""
                        CREATE CONSTRAINT {constraint_name}
                        ON (n:{constraint_req.node_type.value})
                        ASSERT ({properties}) IS NODE KEY
                        """
                    )
                    
                    try:
                        await self.execute_query(query)
                        results.append(True)
                    except Exception as create_err:
                        # If the constraint creation fails, try creating just an index
                        print(f"Constraint creation failed, falling back to index: {create_err}")
                        for prop in constraint_req.property_names:
                            index_query = GraphQuery(
                                cypher_query=f"""
                                CREATE INDEX {constraint_req.node_type.value.lower()}_{prop}_idx
                                FOR (n:{constraint_req.node_type.value})
                                ON (n.{prop})
                                """
                            )
                            try:
                                await self.execute_query(index_query)
                            except Exception as idx_create_err:
                                print(f"Failed to create fallback index: {idx_create_err}")
                        results.append(False)
                else:
                    print(f"Unsupported constraint type: {constraint_req.constraint_type}")
                    results.append(False)
            except Exception as e:
                print(f"Failed to create constraint: {e}")
                results.append(False)
        
        return results
    
    async def find_nodes_by_property(self, node_type: NodeType, property_name: str, 
                                   property_value: Any) -> List[Dict[str, Any]]:
        """Find nodes by a specific property value."""
        query = GraphQuery(
            cypher_query=f"""
            MATCH (n:{node_type.value})
            WHERE n.{property_name} = $property_value
            RETURN n, id(n) as node_id
            """,
            parameters={"property_value": property_value}
        )
        
        result = await self.execute_query(query)
        return result.records
    
    async def find_related_nodes(self, node_id: str, relationship_type: RelationshipType,
                               direction: str = "both", limit: int = 100) -> List[Dict[str, Any]]:
        """Find nodes related to a given node."""
        if direction == "outgoing":
            pattern = f"(n)-[:{relationship_type.value}]->(related)"
        elif direction == "incoming":
            pattern = f"(n)<-[:{relationship_type.value}]-(related)"
        else:  # both
            pattern = f"(n)-[:{relationship_type.value}]-(related)"
        
        query = GraphQuery(
            cypher_query=f"""
            MATCH {pattern}
            WHERE id(n) = $node_id
            RETURN related, id(related) as related_id
            LIMIT $limit
            """,
            parameters={"node_id": node_id, "limit": limit}
        )
        
        result = await self.execute_query(query)
        return result.records
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        stats_queries = [
            ("total_nodes", "MATCH (n) RETURN count(n) as count"),
            ("total_relationships", "MATCH ()-[r]->() RETURN count(r) as count"),
            ("node_types", "MATCH (n) RETURN labels(n) as labels, count(n) as count"),
            ("relationship_types", "MATCH ()-[r]->() RETURN type(r) as type, count(r) as count")
        ]
        
        stats = {}
        for stat_name, cypher_query in stats_queries:
            try:
                query = GraphQuery(cypher_query=cypher_query)
                result = await self.execute_query(query)
                stats[stat_name] = result.records
            except Exception as e:
                print(f"Failed to get {stat_name}: {e}")
                stats[stat_name] = []
        
        return stats 