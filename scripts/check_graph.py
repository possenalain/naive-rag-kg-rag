from src.utils.graph import GraphDatabaseManager
import asyncio

async def main():
    graph = GraphDatabaseManager()
    await graph.initialize()
    
    print("Nodes in Neo4j:")
    result = await graph.execute_query('MATCH (n) RETURN labels(n) as labels, count(n) as count')
    for r in result:
        print(f"  {r['labels']}: {r['count']}")
    
    print("\nRelationships in Neo4j:")
    result = await graph.execute_query('MATCH ()-[r]-() RETURN type(r) as rel_type, count(r) as count')
    for r in result:
        if r['count'] > 0:
            print(f"  {r['rel_type']}: {r['count']}")
    
    print("\nSample nodes:")
    result = await graph.execute_query('MATCH (n) RETURN labels(n) as labels, properties(n) as props LIMIT 5')
    for r in result:
        print(f"  {r['labels']}: {list(r['props'].keys())}")
    
    await graph.close()

if __name__ == "__main__":
    asyncio.run(main())
from src.utils.graph import GraphDatabaseManager
import asyncio

async def main():
    graph = GraphDatabaseManager()
    await graph.initialize()
    
    print("Nodes in Neo4j:")
    result = await graph.execute_query('MATCH (n) RETURN labels(n) as labels, count(n) as count')
    for r in result:
        print(f"  {r['labels']}: {r['count']}")
    
    print("\nRelationships in Neo4j:")
    result = await graph.execute_query('MATCH ()-[r]-() RETURN type(r) as rel_type, count(r) as count')
    for r in result:
        if r['count'] > 0:
            print(f"  {r['rel_type']}: {r['count']}")
    
    print("\nSample nodes:")
    result = await graph.execute_query('MATCH (n) RETURN labels(n) as labels, properties(n) as props LIMIT 5')
    for r in result:
        print(f"  {r['labels']}: {list(r['props'].keys())}")
    
    await graph.close()

if __name__ == "__main__":
    asyncio.run(main())
