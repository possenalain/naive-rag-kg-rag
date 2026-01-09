"""
Runtime patches for Graphiti library to fix Neo4j 5.18+ compatibility.

This module patches the Graphiti library at runtime to ensure all query functions
use APOC-based dynamic label setting instead of the deprecated `SET n:LabelName` syntax.

This approach is sustainable because:
1. Patches persist across virtual environment recreations
2. No manual editing of installed packages required
3. Changes are version controlled in the project
4. Works even when Graphiti is updated (patches apply at runtime)
"""

import logging
from graphiti_core.models.nodes import node_db_queries
from graphiti_core.driver.driver import GraphProvider

logger = logging.getLogger(__name__)


def patch_entity_node_save_query():
    """
    Patch get_entity_node_save_query to use APOC for dynamic label setting.
    
    The issue: Graphiti uses `SET n:LabelName` syntax which doesn't work well
    with dynamic labels and is deprecated in newer Neo4j versions.
    
    The fix: Use `CALL apoc.create.setLabels(n, [labels])` which works in all
    Neo4j 5.x versions with APOC installed.
    """
    original_func = node_db_queries.get_entity_node_save_query
    
    def patched_get_entity_node_save_query(
        provider: GraphProvider, labels: str, has_aoss: bool = False
    ) -> str:
        """Patched version that uses APOC for dynamic label setting."""
        if provider != GraphProvider.NEO4J:
            # Only patch Neo4j queries
            return original_func(provider, labels, has_aoss)
        
        # Build the save embedding query
        save_embedding_query = (
            'WITH n CALL db.create.setNodeVectorProperty(n, "name_embedding", $entity_data.name_embedding)'
            if not has_aoss
            else ''
        )
        
        # Convert labels string to array format for APOC
        # labels is like "Label1:Label2" so we need ["Label1", "Label2"]
        label_list = labels.split(':') if labels else []
        labels_array = str(label_list)  # ["Label1", "Label2"]
        
        return f"""
                MERGE (n:Entity {{uuid: $entity_data.uuid}})
                SET n = $entity_data
                WITH n
                CALL apoc.create.setLabels(n, {labels_array}) YIELD node AS labeled_node
                {save_embedding_query}
                RETURN n.uuid AS uuid"""
    
    node_db_queries.get_entity_node_save_query = patched_get_entity_node_save_query
    logger.info("✓ Patched get_entity_node_save_query for Neo4j 5.18+ compatibility")


def patch_entity_node_save_bulk_query():
    """
    Patch get_entity_node_save_bulk_query to use APOC for dynamic label setting.
    
    This is the bulk version used when adding multiple entities at once.
    """
    original_func = node_db_queries.get_entity_node_save_bulk_query
    
    def patched_get_entity_node_save_bulk_query(
        provider: GraphProvider, nodes: list, has_aoss: bool = False
    ) -> str:
        """Patched bulk version that uses APOC for dynamic label setting."""
        if provider != GraphProvider.NEO4J:
            # Only patch Neo4j queries
            return original_func(provider, nodes, has_aoss)
        
        # Build the save embedding query
        save_embedding_query = (
            'WITH n, node CALL db.create.setNodeVectorProperty(n, "name_embedding", node.name_embedding)'
            if not has_aoss
            else ''
        )
        
        return f"""
                    UNWIND $nodes AS node
                    MERGE (n:Entity {{uuid: node.uuid}})
                    SET n = node
                    WITH n, node
                    CALL apoc.create.setLabels(n, node.labels) YIELD node AS labeled_node
                    {save_embedding_query}
                RETURN n.uuid AS uuid"""
    
    node_db_queries.get_entity_node_save_bulk_query = patched_get_entity_node_save_bulk_query
    logger.info("✓ Patched get_entity_node_save_bulk_query for Neo4j 5.18+ compatibility")


def apply_all_patches():
    """Apply all runtime patches for Graphiti library."""
    try:
        logger.info("Applying Graphiti patches...")
        patch_entity_node_save_query()
        patch_entity_node_save_bulk_query()
        
        # ALSO patch the already-imported reference in bulk_utils
        from graphiti_core.utils import bulk_utils
        bulk_utils.get_entity_node_save_bulk_query = node_db_queries.get_entity_node_save_bulk_query
        logger.info("Patched bulk_utils module reference")
        
        logger.info("All Graphiti Neo4j compatibility patches applied successfully")
    except Exception as e:
        logger.error(f"Failed to apply Graphiti patches: {e}")
        raise
