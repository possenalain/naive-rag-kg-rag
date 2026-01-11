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

# CRITICAL: Apply Graphiti compatibility patches BEFORE importing Graphiti!
# This must happen before any Graphiti modules are loaded to ensure the patches
# are applied to the query functions before they're imported by other modules.
from src.utils.graphiti_patches import apply_all_patches
apply_all_patches()

# Now import Graphiti after patches are applied
from graphiti_core import Graphiti
from graphiti_core.nodes import EntityNode, EpisodicNode, EpisodeType
from graphiti_core.edges import EntityEdge
from graphiti_core.llm_client import LLMConfig
from graphiti_core.llm_client.gemini_client import GeminiClient
from graphiti_core.embedder.gemini import GeminiEmbedder, GeminiEmbedderConfig
from graphiti_core.graphiti import AddEpisodeResults

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
                    auth=(settings.neo4j.user, settings.neo4j.password),
                    max_connection_pool_size=50,
                    connection_acquisition_timeout=60,
                    max_connection_lifetime=3600,
                    keep_alive=True
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
                    embedding_model=settings.embedding.model_name,
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
        source_description: str,
        timeout: int = 120
    ) -> AddEpisodeResults:
        """
        Add an episode (document chunk) to the knowledge graph using Graphiti.
        Graphiti will extract entities and relationships automatically.
        
        Note: Graphiti does not support metadata parameter in add_episode.
        Use source_description to provide context about the episode.
        
        Args:
            timeout: Maximum time in seconds to wait for episode creation (default: 120s)
        
        Returns:
            AddEpisodeResults containing the episode, entities, and relationships
        
        Raises:
            asyncio.TimeoutError: If operation exceeds timeout
        """
        try:
            results = await asyncio.wait_for(
                self.graphiti.add_episode(
                    name=name,
                    episode_body=content,
                    source=EpisodeType.text,
                    source_description=source_description,
                    reference_time=datetime.now()
                ),
                timeout=timeout
            )
            logger.debug(f"Added episode: {name}")
            return results
        except asyncio.TimeoutError:
            logger.error(f"Timeout ({timeout}s) adding episode: {name}")
            raise
    
    async def search_entities(
        self,
        query: str,
        limit: int = 10
    ) -> List[EntityNode]:
        """Search for entities semantically using Graphiti."""
        entities = await self.graphiti.search(
            query=query,
            num_results=limit
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
    
    async def link_chunk_to_episodic(
        self,
        chunk_id: int,
        episodic_uuid: str
    ) -> bool:
        """Link a chunk to its corresponding episodic node."""
        query = """
            MATCH (c:Chunk {chunk_id: $chunk_id})
            MATCH (ep:Episodic {uuid: $episodic_uuid})
            MERGE (c)-[r:HAS_EPISODE]->(ep)
            RETURN count(r) as links_created
        """
        
        async with self.driver.session() as session:
            result = await session.run(
                query,
                chunk_id=chunk_id,
                episodic_uuid=episodic_uuid
            )
            record = await result.single()
        
        success = record['links_created'] > 0
        if success:
            logger.debug(f"Linked chunk {chunk_id} to episodic {episodic_uuid}")
        else:
            logger.warning(f"Failed to link chunk {chunk_id} to episodic {episodic_uuid}")
        return success
    
    # ===== Knowledge Graph RAG Queries =====
    
    async def kg_retrieve(
        self,
        query_text: str,
        top_k: int = 5,
        max_hops: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Knowledge Graph-based retrieval with multi-hop traversal:
        1. Find relevant entities semantically
        2. Expand entities through graph relationships (multi-hop)
        3. Traverse to connected chunks
        4. Rank by relevance (direct matches boosted)
        """
        from config.settings import get_settings
        settings = get_settings()
        
        # Step 1: Search for relevant entities with higher limit for better coverage
        entity_multiplier = getattr(settings.rag, 'entity_search_multiplier', 5)
        search_limit = top_k * entity_multiplier
        search_results = await self.search_entities(query_text, limit=search_limit)
        
        if not search_results:
            logger.warning("No entities found for query")
            return []
        
        # Extract unique entity UUIDs from search results
        direct_entity_ids = set()
        for result in search_results:
            # Graphiti search returns EntityEdge objects
            if hasattr(result, 'source_node_uuid'):
                direct_entity_ids.add(result.source_node_uuid)
            if hasattr(result, 'target_node_uuid'):
                direct_entity_ids.add(result.target_node_uuid)
            # If it's actually an EntityNode, use its UUID directly
            elif hasattr(result, 'uuid') and hasattr(result, 'name'):
                direct_entity_ids.add(result.uuid)
        
        direct_entity_ids = list(direct_entity_ids)
        logger.info(f"Found {len(direct_entity_ids)} direct entities from search")
        
        # Step 2: Multi-hop expansion - find related entities
        enable_multi_hop = getattr(settings.rag, 'kg_enable_multi_hop', True)
        if enable_multi_hop and max_hops > 1:
            # Note: max_hops must be embedded in query string, not passed as parameter
            # Neo4j doesn't allow parameters in variable-length patterns like [*1..$max_hops]
            expansion_query = f"""
                UNWIND $seed_entities as seed_uuid
                MATCH (seed:Entity {{uuid: seed_uuid}})
                MATCH path = (seed)-[*1..{max_hops}]-(related:Entity)
                WITH DISTINCT related, seed, length(path) as distance
                WHERE distance <= {max_hops}
                RETURN related.uuid as entity_uuid, 
                       distance,
                       seed.uuid IN $seed_entities as is_direct
                ORDER BY distance, is_direct DESC
                LIMIT $expansion_limit
            """
            
            async with self.driver.session() as session:
                result = await session.run(
                    expansion_query,
                    seed_entities=direct_entity_ids,
                    expansion_limit=search_limit * 2  # Allow more related entities
                )
                expansion_records = await result.data()
            
            # Combine direct and expanded entities
            all_entity_ids = direct_entity_ids.copy()
            expanded_count = 0
            for record in expansion_records:
                entity_uuid = record['entity_uuid']
                if entity_uuid not in all_entity_ids:
                    all_entity_ids.append(entity_uuid)
                    expanded_count += 1
            
            logger.info(f"Expanded to {len(all_entity_ids)} entities total (+{expanded_count} via multi-hop)")
        else:
            all_entity_ids = direct_entity_ids
            logger.info(f"Multi-hop disabled, using {len(all_entity_ids)} direct entities only")
        
        # Step 3: Get chunks connected to these entities via Episodic nodes
        # Apply relevance boost for direct entity matches
        relevance_boost = getattr(settings.rag, 'kg_relevance_boost', 0.3)
        
        retrieval_query = """
            UNWIND $entity_ids as entity_uuid
            MATCH (e:Entity {uuid: entity_uuid})
            MATCH (e)<-[:MENTIONS]-(ep:Episodic)
            MATCH (c:Chunk)-[:HAS_EPISODE]->(ep)
            WITH c, 
                 COUNT(DISTINCT e) as entity_count,
                 SUM(CASE WHEN e.uuid IN $direct_entities THEN 1 ELSE 0 END) as direct_count,
                 COUNT(DISTINCT ep) as episode_count
            WITH c, entity_count, direct_count, episode_count,
                 (entity_count + (direct_count * $boost)) as relevance_score
            ORDER BY relevance_score DESC, episode_count DESC
            LIMIT $top_k
            RETURN c.chunk_id as chunk_id,
                   c.chunk_text as chunk_text,
                   c.document_id as document_id,
                   c.chunk_index as chunk_index,
                   relevance_score,
                   entity_count,
                   direct_count,
                   episode_count
        """
        
        async with self.driver.session() as session:
            result = await session.run(
                retrieval_query,
                entity_ids=all_entity_ids,
                direct_entities=direct_entity_ids,
                boost=relevance_boost,
                top_k=top_k
            )
            records = await result.data()
        
        logger.info(f"KG retrieval returned {len(records)} chunks (max_hops={max_hops}, entities={len(all_entity_ids)})")
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
