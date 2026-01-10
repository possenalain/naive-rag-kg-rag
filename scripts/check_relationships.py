from neo4j import GraphDatabase
from config.settings import get_settings

settings = get_settings()
driver = GraphDatabase.driver(settings.neo4j.uri, auth=(settings.neo4j.user, settings.neo4j.password))

print("How are Episodic and Entity nodes connected?")
with driver.session() as session:
    # Check relationships between Episode and Entity
    result = session.run("""
        MATCH (ep:Episodic)-[r]-(e:Entity)
        RETURN type(r) as rel_type, count(*) as count
        LIMIT 10
    """)
    for r in result:
        print(f"  {r['rel_type']}: {r['count']}")

print("\nHow can we get from Chunk to Entity?")
print("Chunks exist: 2")
print("Entities exist: 28")
print("Episodic exist: 2")
print("\nLet's check if Chunks have relationships:")
with driver.session() as session:
    result = session.run("""
        MATCH (c:Chunk)-[r]-()
        RETURN type(r) as rel_type, count(*) as count
    """)
    has_rels = False
    for r in result:
        has_rels = True
        print(f"  {r['rel_type']}: {r['count']}")
    if not has_rels:
        print("  No relationships found for Chunk nodes!")

print("\nLet's see an example Episodic node:")
with driver.session() as session:
    result = session.run("""
        MATCH (ep:Episodic)
        RETURN ep.name as name, ep.source_description as desc
        LIMIT 1
    """)
    for r in result:
        print(f"  Name: {r['name']}")
        print(f"  Source: {r['desc'][:100]}...")

driver.close()
