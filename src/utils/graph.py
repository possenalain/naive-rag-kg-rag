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
        limit: int = 10,
        min_similarity: Optional[float] = None
    ) -> List[EntityNode]:
        """
        Search for entities semantically using Graphiti.
        
        Graphiti's search uses hybrid retrieval (BM25 + vector similarity) with 
        reranking (RRF), so results are already relevant and ranked. We fetch 
        what we need and let Graphiti's filtering do the work.
        
        Args:
            query: Search query text
            limit: Maximum number of entities to return
            min_similarity: Ignored - kept for API compatibility but has no effect
                           since Graphiti doesn't expose similarity scores
        
        Returns:
            List of EntityEdge objects (facts/relationships)
        """
        # Graphiti's search already does:
        # 1. Hybrid search (BM25 + cosine similarity)
        # 2. Relevance filtering (min_score = 0.6 by default)
        # 3. Reranking (RRF combines both search methods)
        # So we just fetch what we need - Graphiti handles the quality
        
        search_results = await self.graphiti.search(
            query=query,
            num_results=limit
        )
        
        if not search_results:
            logger.debug(f"No entities found for query: {query}")
            return []
        
        # Graphiti.search() returns EntityEdge objects (facts/relationships)
        logger.info(
            f"Entity search returned {len(search_results)} edges/facts from Graphiti "
            f"(hybrid BM25 + vector search with RRF reranking)"
        )
        
        return search_results
    
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
        max_hops: int = 2,
        max_chunks: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Knowledge Graph-based retrieval with multi-hop traversal:
        1. Find relevant entities semantically
        2. Expand entities through graph relationships (multi-hop)
        3. Traverse to connected chunks
        4. Rank by relevance (direct matches boosted)
        
        Args:
            query_text: Search query
            top_k: Number of chunks to return (deprecated, use max_chunks)
            max_hops: Maximum hops for entity expansion
            max_chunks: Maximum chunks to return (safety cap, default=20).
                       Returns all chunks >= min_entity_ratio up to this limit.
        """
        from config.settings import get_settings
        settings = get_settings()
        
        # Step 1: Search for relevant entities using Graphiti's hybrid search
        # Graphiti combines BM25 + vector similarity with RRF reranking, so results
        # are already filtered and ranked by relevance
        entity_multiplier = getattr(settings.rag, 'entity_search_multiplier', 3)
        min_entity_similarity = getattr(settings.rag, 'kg_min_entity_similarity', 0.5)
        search_limit = top_k * entity_multiplier
        
        search_results = await self.search_entities(
            query_text, 
            limit=search_limit,
            min_similarity=min_entity_similarity
        )
        
        if not search_results:
            logger.warning(
                f"No entities found for query. Try adjusting RAG_KG_MIN_ENTITY_SIMILARITY or RAG_ENTITY_SEARCH_MULTIPLIER"
            )
            return []
        
        # Extract unique entity UUIDs from search results (EntityEdge objects)
        direct_entity_ids = set()
        for result in search_results:
            # Graphiti search returns EntityEdge objects with source/target entity UUIDs
            if hasattr(result, 'source_node_uuid'):
                direct_entity_ids.add(result.source_node_uuid)
            if hasattr(result, 'target_node_uuid'):
                direct_entity_ids.add(result.target_node_uuid)
            # Fallback: if it's an EntityNode, use its UUID directly
            elif hasattr(result, 'uuid') and hasattr(result, 'name'):
                direct_entity_ids.add(result.uuid)
        
        direct_entity_ids = list(direct_entity_ids)
        
        logger.info(f"Extracted {len(direct_entity_ids)} unique entities from {len(search_results)} edges")
        
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
            
            # Combine direct and expanded entities with distance-based weights
            # Direct entities = 1.0, 1-hop = 0.5, 2-hop = 0.25 (exponential decay)
            entity_weights = {}
            for entity_id in direct_entity_ids:
                entity_weights[entity_id] = 1.0
            
            all_entity_ids = direct_entity_ids.copy()
            expanded_count = 0
            for record in expansion_records:
                entity_uuid = record['entity_uuid']
                distance = record['distance']
                if entity_uuid not in all_entity_ids:
                    all_entity_ids.append(entity_uuid)
                    entity_weights[entity_uuid] = 1.0 / (2 ** distance)  # 0.5 for hop 1, 0.25 for hop 2
                    expanded_count += 1
            
            logger.info(
                f"Expanded to {len(all_entity_ids)} entities total (+{expanded_count} via multi-hop, "
                f"weights: direct={sum(1 for w in entity_weights.values() if w == 1.0)}, "
                f"1-hop={sum(1 for w in entity_weights.values() if 0.4 < w < 0.6)}, "
                f"2-hop={sum(1 for w in entity_weights.values() if w < 0.3)})"
            )
        else:
            # No expansion - all entities get full weight
            entity_weights = {entity_id: 1.0 for entity_id in direct_entity_ids}
            all_entity_ids = direct_entity_ids
            logger.info(f"Multi-hop disabled, using {len(all_entity_ids)} direct entities only")
        
        # Step 3: Get chunks connected to these entities via Episodic nodes
        # Use precision-based scoring that heavily favors high direct-entity ratios
        relevance_boost = getattr(settings.rag, 'kg_relevance_boost', 0.3)
        min_entity_ratio = getattr(settings.rag, 'kg_min_entity_ratio', 0.3)
        
        # Two-stage filtering with weighted scoring:
        # 1. Filter by direct_recall: direct_count / query_entity_count (MUST have direct entities!)
        # 2. Score by weighted_direct_count: includes expanded entities with distance decay
        # 3. This prevents chunks with only expanded entities from passing filter
        retrieval_query = """
            UNWIND $entity_ids as entity_uuid
            MATCH (e:Entity {uuid: entity_uuid})
            MATCH (e)<-[:MENTIONS]-(ep:Episodic)
            MATCH (c:Chunk)-[:HAS_EPISODE]->(ep)
            WITH c, 
                 COUNT(DISTINCT e) as entity_count,
                 SUM(CASE WHEN e.uuid IN keys($entity_weights) THEN $entity_weights[e.uuid] ELSE 0.0 END) as weighted_direct_count,
                 COUNT(DISTINCT CASE WHEN e.uuid IN $direct_entities THEN e.uuid ELSE null END) as direct_count,
                 COUNT(DISTINCT ep) as episode_count
            WITH c, entity_count, weighted_direct_count, direct_count, episode_count,
                 toFloat(direct_count) / toFloat(size($direct_entities)) as direct_recall
            WHERE direct_recall >= $min_ratio
            WITH c, entity_count, weighted_direct_count, direct_count, episode_count, direct_recall,
                 (weighted_direct_count * weighted_direct_count * direct_recall * $boost) as relevance_score
            ORDER BY relevance_score DESC, weighted_direct_count DESC, episode_count DESC
            LIMIT $limit
            RETURN c.chunk_id as chunk_id,
                   c.chunk_text as chunk_text,
                   c.document_id as document_id,
                   c.chunk_index as chunk_index,
                   relevance_score,
                   entity_count,
                   direct_count,
                   weighted_direct_count,
                   episode_count,
                   direct_recall
        """
        
        # Use max_chunks if provided (for threshold-based retrieval), otherwise use top_k
        # Default to 20 as safety cap to prevent token explosion
        limit = max_chunks if max_chunks is not None else (20 if max_chunks is None and top_k == 5 else top_k)
        
        async with self.driver.session() as session:
            result = await session.run(
                retrieval_query,
                entity_ids=all_entity_ids,
                direct_entities=direct_entity_ids,
                entity_weights=entity_weights,
                boost=relevance_boost,
                min_ratio=min_entity_ratio,
                limit=limit
            )
            records = await result.data()
        
        # Log detailed statistics for debugging
        if records:
            avg_recall = sum(r.get('direct_recall', 0) for r in records) / len(records)
            avg_direct = sum(r.get('direct_count', 0) for r in records) / len(records)
            avg_weighted = sum(r.get('weighted_direct_count', 0) for r in records) / len(records)
            logger.info(
                f"KG retrieval: {len(records)} chunks, "
                f"avg direct_recall={avg_recall:.2f}, avg weighted_count={avg_weighted:.1f}, "
                f"avg direct_count={avg_direct:.1f}, entities={len(all_entity_ids)}, min_ratio={min_entity_ratio}"
            )
        else:
            logger.warning(
                f"KG retrieval returned 0 chunks! "
                f"Try lowering min_entity_ratio (current: {min_entity_ratio}) "
                f"or increasing entity_search_multiplier"
            )
        
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
