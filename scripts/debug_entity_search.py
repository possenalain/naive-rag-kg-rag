import asyncio
from src.utils.graph import GraphDatabaseManager

async def main():
    graph = GraphDatabaseManager()
    await graph.initialize()
    
    query = "What did OpenAI raise in funding?"
    print(f"Query: {query}\n")
    
    entities = await graph.search_entities(query, limit=5)
    
    print(f"Found {len(entities)} entities:")
    for i, ent in enumerate(entities, 1):
        print(f"{i}. Type: {type(ent)}, {ent}")
        # Try different attributes
        if hasattr(ent, 'name'):
            print(f"   Name: {ent.name}")
        if hasattr(ent, 'uuid'):
            print(f"   UUID: {ent.uuid}")
        if hasattr(ent, 'fact'):
            print(f"   Fact: {ent.fact[:80]}...")
    
    await graph.close()

asyncio.run(main())
