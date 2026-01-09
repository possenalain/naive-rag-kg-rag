"""
Neo4j graph database utilities with Graphiti integration.
Provides graph operations, traversal, and knowledge graph management.
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from neo4j import AsyncGraphDatabase, AsyncDriver
from neo4j.exceptions import ServiceUnavailable
import logging
from datetime import datetime
from graphiti_core import Graphiti
from graphiti_core.nodes import EntityNode, EpisodicNode, EpisodeType
from graphiti_core.edges import EntityEdge
from graphiti_core.llm_client import LLMConfig
from graphiti_core.llm_client.gemini_client import GeminiClient
from graphiti_core.embedder.gemini import GeminiEmbedder, GeminiEmbedderConfig

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GraphDatabaseManager:
    """Manages Neo4j connection and graph operations."""
    
    def __init__(self):
        self.driver: Optional[AsyncDriver] = None
        self.graphiti: Optional[Graphiti] = None
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """Initialize Neo4j driver and Graphiti client."""
        async with self._lock:
            if self.driver is not None:
                logger.warning("Graph database already initialized")
                return
            
            try:
                self.driver = AsyncGraphDatabase.driver(
                    settings.neo4j.uri,
                    auth=(settings.neo4j.user, settings.neo4j.password)
                )
                
                # Verify connection
                async with self.driver.session() as session:
                    result = await session.run("RETURN 1 as num")
                    await result.single()
                
                logger.info("Neo4j driver initialized")
                
                # Initialize Graphiti with Google Gemini clients
                llm_config = LLMConfig(
                    api_key=settings.llm.api_key,
                    model=settings.llm.model_name,
                )
                llm_client = GeminiClient(llm_config)
                
                embedder_config = GeminiEmbedderConfig(
                    api_key=settings.embedding.api_key,
                    model=settings.embedding.model_name,
                    embedding_dim=settings.embedding.dimensions,
                )
                embedder_client = GeminiEmbedder(embedder_config)
                
                self.graphiti = Graphiti(
                    uri=settings.neo4j.uri,
                    user=settings.neo4j.user,
                    password=settings.neo4j.password,
                    llm_client=llm_client,
                    embedder=embedder_client,
                )
                await self.graphiti.build_indices_and_constraints()
                logger.info("Graphiti initialized with Google Gemini LLM and embedder")
                
            except ServiceUnavailable as e:
                logger.error(f"Failed to connect to Neo4j: {e}")
                raise
            except Exception as e:
                logger.error(f"Failed to initialize graph database: {e}")
                raise
    
    async def close(self) -> None:
        """Close Neo4j driver."""
        async with self._lock:
            if self.driver:
                await self.driver.close()
                self.driver = None
                logger.info("Neo4j driver closed")
    
    # ===== Chunk Node Operations =====
    
    async def create_chunk_node(
        self,
        chunk_id: int,
        chunk_text: str,
        document_id: int,
        chunk_index: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a chunk node in Neo4j."""
        query = """
            CREATE (c:Chunk {
                chunk_id: $chunk_id,
                chunk_text: $chunk_text,
                document_id: $document_id,
                chunk_index: $chunk_index,
                metadata: $metadata,
                created_at: datetime()
            })
            RETURN elementId(c) as node_id
        """
        
        async with self.driver.session() as session:
            result = await session.run(
                query,
                chunk_id=chunk_id,
                chunk_text=chunk_text,
                document_id=document_id,
                chunk_index=chunk_index,
                metadata=metadata or {}
            )
            record = await result.single()
        
        node_id = record['node_id']
        logger.debug(f"Created chunk node: {node_id}")
        return node_id
    
    async def bulk_create_chunk_nodes(
        self,
        chunks: List[Dict[str, Any]]
    ) -> List[str]:
        """Bulk create chunk nodes."""
        query = """
            UNWIND $chunks as chunk
            CREATE (c:Chunk {
                chunk_id: chunk.chunk_id,
                chunk_text: chunk.chunk_text,
                document_id: chunk.document_id,
                chunk_index: chunk.chunk_index,
                metadata: chunk.metadata,
                created_at: datetime()
            })
            RETURN elementId(c) as node_id
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, chunks=chunks)
            records = await result.data()
        
        node_ids = [record['node_id'] for record in records]
        logger.info(f"Bulk created {len(node_ids)} chunk nodes")
        return node_ids
    
    async def get_chunk_node(self, chunk_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a chunk node by ID."""
        query = """
            MATCH (c:Chunk {chunk_id: $chunk_id})
            RETURN c, elementId(c) as node_id
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, chunk_id=chunk_id)
            record = await result.single()
        
        if not record:
            return None
        
        node = dict(record['c'])
        node['node_id'] = record['node_id']
        return node
    
    # ===== Entity Operations (via Graphiti) =====
    
    async def add_episode(
        self,
        name: str,
        content: str,
        source_description: str
    ) -> EpisodicNode:
        """
        Add an episode (document chunk) to the knowledge graph using Graphiti.
        Graphiti will extract entities and relationships automatically.
        
        Note: Graphiti does not support metadata parameter in add_episode.
        Use source_description to provide context about the episode.
        """
        episode = await self.graphiti.add_episode(
            name=name,
            episode_body=content,
            source=EpisodeType.text,
            source_description=source_description,
            reference_time=datetime.now()
        )
        logger.debug(f"Added episode: {name}")
        return episode
    
    async def search_entities(
        self,
        query: str,
        limit: int = 10
    ) -> List[EntityNode]:
        """Search for entities semantically using Graphiti."""
        entities = await self.graphiti.search(
            query=query,
            limit=limit
        )
        logger.debug(f"Found {len(entities)} entities for query: {query}")
        return entities
    
    async def get_entity(self, entity_id: str) -> Optional[EntityNode]:
        """Get an entity by ID."""
        query = """
            MATCH (e:Entity)
            WHERE elementId(e) = $entity_id
            RETURN e
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, entity_id=entity_id)
            record = await result.single()
        
        if not record:
            return None
        
        return record['e']
    
    # ===== Graph Traversal =====
    
    async def get_entity_neighborhood(
        self,
        entity_id: str,
        max_hops: int = 2,
        limit_per_hop: int = 10
    ) -> Dict[str, Any]:
        """
        Get entity neighborhood with multi-hop traversal.
        Returns entities and relationships within max_hops.
        """
        query = """
            MATCH path = (start:Entity)-[*1..$max_hops]-(neighbor)
            WHERE elementId(start) = $entity_id
            WITH DISTINCT neighbor, length(path) as distance
            ORDER BY distance
            LIMIT $limit
            RETURN collect(neighbor) as neighbors
        """
        
        async with self.driver.session() as session:
            result = await session.run(
                query,
                entity_id=entity_id,
                max_hops=max_hops,
                limit=limit_per_hop * max_hops
            )
            record = await result.single()
        
        if not record:
            return {"neighbors": []}
        
        return {"neighbors": record['neighbors']}
    
    async def find_paths_between_entities(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5
    ) -> List[Dict[str, Any]]:
        """Find all paths between two entities up to max_depth."""
        query = """
            MATCH path = shortestPath(
                (source:Entity)-[*..=$max_depth]-(target:Entity)
            )
            WHERE elementId(source) = $source_id
              AND elementId(target) = $target_id
            RETURN path,
                   [node in nodes(path) | node.name] as node_names,
                   [rel in relationships(path) | type(rel)] as rel_types,
                   length(path) as path_length
            ORDER BY path_length
            LIMIT 5
        """
        
        async with self.driver.session() as session:
            result = await session.run(
                query,
                source_id=source_id,
                target_id=target_id,
                max_depth=max_depth
            )
            records = await result.data()
        
        paths = []
        for record in records:
            paths.append({
                'node_names': record['node_names'],
                'relationship_types': record['rel_types'],
                'length': record['path_length']
            })
        
        logger.debug(f"Found {len(paths)} paths between entities")
        return paths
    
    async def get_connected_chunks(
        self,
        chunk_id: int,
        max_hops: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Get chunks connected through the knowledge graph.
        Traverses: Chunk -> Entity -> Entity -> Chunk
        """
        query = """
            MATCH (start:Chunk {chunk_id: $chunk_id})
            MATCH (start)-[:HAS_ENTITY]->(e1:Entity)
            MATCH (e1)-[*0..$max_hops]-(e2:Entity)
            MATCH (e2)<-[:HAS_ENTITY]-(end:Chunk)
            WHERE start <> end
            WITH DISTINCT end, COUNT(DISTINCT e2) as shared_entities
            ORDER BY shared_entities DESC
            LIMIT 10
            RETURN end.chunk_id as chunk_id,
                   end.chunk_text as chunk_text,
                   end.document_id as document_id,
                   shared_entities
        """
        
        async with self.driver.session() as session:
            result = await session.run(
                query,
                chunk_id=chunk_id,
                max_hops=max_hops
            )
            records = await result.data()
        
        logger.debug(f"Found {len(records)} connected chunks for chunk {chunk_id}")
        return records
    
    # ===== Chunk-Entity Relationships =====
    
    async def link_chunk_to_entities(
        self,
        chunk_id: int,
        entity_ids: List[str]
    ) -> int:
        """Link a chunk to extracted entities."""
        query = """
            MATCH (c:Chunk {chunk_id: $chunk_id})
            UNWIND $entity_ids as entity_id
            MATCH (e:Entity)
            WHERE elementId(e) = entity_id
            MERGE (c)-[r:HAS_ENTITY]->(e)
            RETURN count(r) as links_created
        """
        
        async with self.driver.session() as session:
            result = await session.run(
                query,
                chunk_id=chunk_id,
                entity_ids=entity_ids
            )
            record = await result.single()
        
        links = record['links_created']
        logger.debug(f"Linked chunk {chunk_id} to {links} entities")
        return links
    
    # ===== Knowledge Graph RAG Queries =====
    
    async def kg_retrieve(
        self,
        query_text: str,
        top_k: int = 5,
        max_hops: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Knowledge Graph-based retrieval:
        1. Find relevant entities semantically
        2. Traverse to connected chunks
        3. Rank by relevance
        """
        # Step 1: Search for relevant entities
        entities = await self.search_entities(query_text, limit=top_k * 2)
        
        if not entities:
            logger.warning("No entities found for query")
            return []
        
        entity_ids = [entity.uuid for entity in entities]
        
        # Step 2: Get chunks connected to these entities
        query = """
            UNWIND $entity_ids as entity_id
            MATCH (e:Entity)
            WHERE elementId(e) = entity_id
            MATCH (e)<-[:HAS_ENTITY]-(c:Chunk)
            WITH DISTINCT c, COUNT(DISTINCT e) as entity_count
            ORDER BY entity_count DESC
            LIMIT $top_k
            RETURN c.chunk_id as chunk_id,
                   c.chunk_text as chunk_text,
                   c.document_id as document_id,
                   c.chunk_index as chunk_index,
                   entity_count as relevance_score
        """
        
        async with self.driver.session() as session:
            result = await session.run(
                query,
                entity_ids=entity_ids,
                top_k=top_k
            )
            records = await result.data()
        
        logger.info(f"KG retrieval returned {len(records)} chunks")
        return records
    
    async def hybrid_kg_retrieve(
        self,
        query_text: str,
        relevant_chunk_ids: List[int],
        top_k: int = 5,
        max_hops: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Hybrid retrieval combining vector search results with graph traversal.
        Expands from vector-retrieved chunks via the knowledge graph.
        """
        if not relevant_chunk_ids:
            logger.warning("No chunks provided for hybrid KG retrieval")
            return []
        
        # Expand from relevant chunks through graph
        query = """
            MATCH (start:Chunk)
            WHERE start.chunk_id IN $chunk_ids
            MATCH (start)-[:HAS_ENTITY]->(e1:Entity)
            MATCH (e1)-[*0..$max_hops]-(e2:Entity)
            MATCH (e2)<-[:HAS_ENTITY]-(end:Chunk)
            WITH DISTINCT end, 
                 COUNT(DISTINCT e2) as shared_entities,
                 CASE WHEN end.chunk_id IN $chunk_ids THEN 1.0 ELSE 0.5 END as boost
            ORDER BY (shared_entities * boost) DESC
            LIMIT $top_k
            RETURN end.chunk_id as chunk_id,
                   end.chunk_text as chunk_text,
                   end.document_id as document_id,
                   end.chunk_index as chunk_index,
                   shared_entities,
                   boost,
                   (shared_entities * boost) as relevance_score
        """
        
        async with self.driver.session() as session:
            result = await session.run(
                query,
                chunk_ids=relevant_chunk_ids,
                max_hops=max_hops,
                top_k=top_k
            )
            records = await result.data()
        
        logger.info(f"Hybrid KG retrieval returned {len(records)} chunks")
        return records
    
    # ===== Utility Methods =====
    
    async def get_graph_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge graph."""
        query = """
            MATCH (c:Chunk) WITH COUNT(c) as chunk_count
            MATCH (e:Entity) WITH chunk_count, COUNT(e) as entity_count
            MATCH ()-[r:HAS_ENTITY]->() WITH chunk_count, entity_count, COUNT(r) as link_count
            MATCH (e1:Entity)-[rel]-(e2:Entity)
            RETURN chunk_count, entity_count, link_count, COUNT(DISTINCT rel) as entity_relations
        """
        
        async with self.driver.session() as session:
            result = await session.run(query)
            record = await result.single()
        
        if not record:
            return {"chunk_count": 0, "entity_count": 0, "link_count": 0, "entity_relations": 0}
        
        return dict(record)
    
    async def clear_graph(self) -> Dict[str, int]:
        """Clear all nodes and relationships from the graph."""
        query = """
            MATCH (n)
            DETACH DELETE n
            RETURN count(n) as deleted_count
        """
        
        async with self.driver.session() as session:
            result = await session.run(query)
            record = await result.single()
        
        deleted = record['deleted_count']
        logger.warning(f"Cleared graph: {deleted} nodes deleted")
        return {"deleted_count": deleted}


# Global graph manager instance
graph_manager = GraphDatabaseManager()


async def get_graph() -> GraphDatabaseManager:
    """Get graph database manager instance."""
    if not graph_manager.driver:
        await graph_manager.initialize()
    return graph_manager


if __name__ == "__main__":
    import sys
    
    async def init_graph():
        """Initialize graph database with indices and constraints."""
        try:
            await graph_manager.initialize()
            logger.info("Graph database initialized successfully")
            await graph_manager.close()
            return True
        except Exception as e:
            logger.error(f"Failed to initialize graph database: {e}")
            await graph_manager.close()
            return False
    
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        logging.basicConfig(level=logging.INFO)
        success = asyncio.run(init_graph())
        sys.exit(0 if success else 1)
    else:
        print("Usage: python -m src.utils.graph init")
        sys.exit(1)
