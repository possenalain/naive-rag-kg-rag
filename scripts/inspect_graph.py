from neo4j import GraphDatabase
from config.settings import get_settings

settings = get_settings()
driver = GraphDatabase.driver(settings.neo4j.uri, auth=(settings.neo4j.user, settings.neo4j.password))

print("Nodes in Neo4j:")
with driver.session() as session:
    result = session.run('MATCH (n) RETURN labels(n) as labels, count(n) as count')
    for r in result:
        print(f"  {r['labels']}: {r['count']}")

print("\nRelationships in Neo4j:")
with driver.session() as session:
    result = session.run('MATCH ()-[r]-() RETURN type(r) as rel_type, count(r) as count')
    for r in result:
        if r['count'] > 0:
            print(f"  {r['rel_type']}: {r['count']}")

print("\nSample Chunk nodes:")
with driver.session() as session:
    result = session.run('MATCH (c:Chunk) RETURN properties(c) as props LIMIT 2')
    for r in result:
        props = r['props']
        print(f"  chunk_id: {props.get('chunk_id')}, document_id: {props.get('document_id')}")

print("\nSample Entity nodes:")
with driver.session() as session:
    result = session.run('MATCH (e:Entity) RETURN properties(e) as props LIMIT 2')
    for r in result:
        props = r['props']
        print(f"  name: {props.get('name')}, summary: {props.get('summary', 'N/A')[:50]}")

driver.close()
