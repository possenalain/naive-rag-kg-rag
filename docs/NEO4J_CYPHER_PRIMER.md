# Neo4j & Cypher Query Language Primer

## 🌐 What is Neo4j?

Neo4j is a **graph database** that stores data as:
- **Nodes** (entities/things) - like people, companies, concepts
- **Relationships** (connections) - how nodes are related
- **Properties** (attributes) - data about nodes and relationships

Unlike SQL tables with rows and columns, Neo4j naturally represents connected data.

## 🎯 Accessing Neo4j Browser

**URL:** http://localhost:7474

**Login:**
- URI: `bolt://localhost:7687`
- Username: `neo4j`
- Password: `neo4jPass123`

## 📊 Your Knowledge Graph Structure

Your RAG system uses these node types:

### Node Labels
- **`:Entity`** - Named entities extracted from documents (people, companies, concepts)
- **`:Episodic`** - Document chunks/episodes from your ingested content
- **`:Chunk`** - Document chunks stored separately

### Relationship Types
- **`:RELATES_TO`** - Connects entities that have relationships
- **`:MENTIONS`** - Links episodic nodes to entities they mention
- **`:NEXT`** - Sequential connections between chunks

### Common Properties
- `uuid` - Unique identifier
- `name` - Entity/node name
- `content` - Text content (for Episodic nodes)
- `summary` - Brief description
- `created_at` - Timestamp
- `embedding` - Vector embedding (for similarity search)

---

## 🔍 Cypher Basics

### Anatomy of a Cypher Query

```cypher
MATCH (pattern)
WHERE condition
RETURN results
```

### Node Syntax
```cypher
()              // Any node
(n)             // Node with variable name 'n'
(e:Entity)      // Node with label 'Entity'
(e:Entity {name: "OpenAI"})  // Node with label and property
```

### Relationship Syntax
```cypher
-[r]->          // Directed relationship
-[r:RELATES_TO]-> // Relationship with type
<-[r]-          // Relationship pointing left
-[r]-           // Undirected relationship
```

---

## 🚀 Essential Queries for Your Knowledge Graph

### 1. **Count All Nodes**
```cypher
MATCH (n)
RETURN labels(n) AS Type, count(n) AS Count
```
Shows how many of each node type you have.

### 2. **View All Entities**
```cypher
MATCH (e:Entity)
RETURN e.name AS Name, e.summary AS Description
LIMIT 20
```

### 3. **View Entity with All Properties**
```cypher
MATCH (e:Entity)
RETURN e
LIMIT 10
```

### 4. **Find Specific Entity**
```cypher
MATCH (e:Entity)
WHERE e.name CONTAINS "OpenAI"
RETURN e
```

### 5. **View Entity Relationships**
```cypher
MATCH (e1:Entity)-[r:RELATES_TO]->(e2:Entity)
RETURN e1.name AS From, 
       type(r) AS Relationship, 
       r.fact AS RelationshipFact,
       e2.name AS To
LIMIT 20
```

### 6. **Visualize Entity Network**
```cypher
MATCH (e1:Entity)-[r:RELATES_TO]->(e2:Entity)
RETURN e1, r, e2
LIMIT 50
```
This shows the graph visually in Neo4j Browser!

### 7. **Find Connected Entities (Path Query)**
```cypher
MATCH path = (start:Entity {name: "OpenAI"})-[:RELATES_TO*1..2]->(end:Entity)
RETURN path
LIMIT 10
```
`*1..2` means 1 to 2 hops away.

### 8. **View Episodic Nodes Mentioning Entities**
```cypher
MATCH (ep:Episodic)-[m:MENTIONS]->(e:Entity)
RETURN ep.content AS Episode, 
       e.name AS Entity
LIMIT 10
```

### 9. **Find All Entities Mentioned in a Document**
```cypher
MATCH (ep:Episodic {source: "doc1_openai_funding.md"})-[:MENTIONS]->(e:Entity)
RETURN e.name AS Entity, e.summary AS Description
```

### 10. **Find Entities with Most Relationships**
```cypher
MATCH (e:Entity)-[r:RELATES_TO]->()
RETURN e.name AS Entity, count(r) AS NumRelationships
ORDER BY NumRelationships DESC
LIMIT 10
```

---

## 🎨 Advanced Query Patterns

### Pattern 1: Find Common Entities Between Documents
```cypher
MATCH (ep1:Episodic)-[:MENTIONS]->(e:Entity)<-[:MENTIONS]-(ep2:Episodic)
WHERE ep1.source <> ep2.source
RETURN e.name AS SharedEntity, 
       collect(DISTINCT ep1.source) AS Documents
```

### Pattern 2: Find Entity Clusters (Highly Connected Entities)
```cypher
MATCH (e:Entity)-[r:RELATES_TO]-(connected:Entity)
WITH e, count(connected) AS degree
WHERE degree > 2
RETURN e.name AS Entity, degree AS Connections
ORDER BY degree DESC
```

### Pattern 3: Shortest Path Between Entities
```cypher
MATCH (start:Entity {name: "OpenAI"}),
      (end:Entity {name: "Amazon"}),
      path = shortestPath((start)-[:RELATES_TO*]-(end))
RETURN path
```

### Pattern 4: Find Entities Within N Hops
```cypher
MATCH (start:Entity {name: "OpenAI"})-[:RELATES_TO*1..3]-(related:Entity)
RETURN DISTINCT related.name AS RelatedEntity
```

### Pattern 5: Aggregate Statistics
```cypher
MATCH (e:Entity)
OPTIONAL MATCH (e)-[r:RELATES_TO]->()
RETURN e.name AS Entity,
       count(r) AS OutgoingRelations,
       e.created_at AS CreatedAt
ORDER BY OutgoingRelations DESC
```

---

## 🔨 Data Modification Queries

### Create a New Entity
```cypher
CREATE (e:Entity {
  uuid: randomUUID(),
  name: "New Entity",
  summary: "Description here",
  created_at: datetime()
})
RETURN e
```

### Create a Relationship
```cypher
MATCH (a:Entity {name: "Entity A"}),
      (b:Entity {name: "Entity B"})
CREATE (a)-[r:RELATES_TO {
  fact: "They are related",
  created_at: datetime()
}]->(b)
RETURN a, r, b
```

### Update Properties
```cypher
MATCH (e:Entity {name: "OpenAI"})
SET e.summary = "Updated description"
RETURN e
```

### Delete a Relationship
```cypher
MATCH (:Entity)-[r:RELATES_TO {uuid: "relationship-uuid"}]->(:Entity)
DELETE r
```

### Delete a Node and Its Relationships
```cypher
MATCH (e:Entity {name: "Node to Delete"})
DETACH DELETE e
```
⚠️ `DETACH DELETE` removes the node AND all its relationships.

---

## 📈 Performance Tips

### 1. **Always Use LIMIT** (While Exploring)
```cypher
MATCH (n) RETURN n LIMIT 100
```
Prevents overwhelming results.

### 2. **Use Indexes** (Already created in your system)
```cypher
// Check existing indexes
SHOW INDEXES
```

### 3. **Use EXPLAIN to See Query Plan**
```cypher
EXPLAIN
MATCH (e:Entity)-[:RELATES_TO]->(e2)
RETURN e, e2
LIMIT 10
```

### 4. **Use PROFILE to See Performance Stats**
```cypher
PROFILE
MATCH (e:Entity)
WHERE e.name CONTAINS "OpenAI"
RETURN e
```

---

## 🎯 Queries Specific to Your RAG System

### Query 1: Find Context for a Question
```cypher
// Find entities related to "funding" topic
MATCH (e:Entity)
WHERE e.name CONTAINS "funding" OR e.summary CONTAINS "funding"
MATCH (e)-[r:RELATES_TO]-(related:Entity)
RETURN e, r, related
LIMIT 30
```

### Query 2: Expand Knowledge Around an Entity
```cypher
// Multi-hop expansion
MATCH (center:Entity {name: "OpenAI"})
MATCH path = (center)-[:RELATES_TO*1..2]-(neighbor:Entity)
RETURN path
```

### Query 3: Find Source Documents for an Entity
```cypher
MATCH (ep:Episodic)-[:MENTIONS]->(e:Entity {name: "OpenAI"})
RETURN DISTINCT ep.source AS Document,
       ep.content AS Context
```

### Query 4: Find Related Entities for RAG Context
```cypher
// Given a query entity, find its immediate neighbors
MATCH (e:Entity {name: "Anthropic"})
MATCH (e)-[:RELATES_TO]-(related:Entity)
RETURN related.name AS Entity,
       related.summary AS Description
```

---

## 🧪 Interactive Learning Queries

Try these in order to learn Cypher:

### Step 1: See What You Have
```cypher
MATCH (n)
RETURN DISTINCT labels(n) AS NodeTypes, count(n) AS Count
```

### Step 2: Explore Entities
```cypher
MATCH (e:Entity)
RETURN e.name, e.summary
LIMIT 10
```

### Step 3: See Relationships
```cypher
MATCH (a)-[r]->(b)
RETURN labels(a) AS From, 
       type(r) AS Relationship, 
       labels(b) AS To
LIMIT 10
```

### Step 4: Visualize a Small Subgraph
```cypher
MATCH (e:Entity)
WITH e LIMIT 5
MATCH (e)-[r]-(connected)
RETURN e, r, connected
```

### Step 5: Filter and Search
```cypher
MATCH (e:Entity)
WHERE e.name CONTAINS "AI" OR e.summary CONTAINS "artificial intelligence"
RETURN e.name, e.summary
```

---

## 📚 Cypher Cheat Sheet

| Operation | Syntax | Example |
|-----------|--------|---------|
| Match any node | `()` | `MATCH (n) RETURN n` |
| Match with label | `(:Label)` | `MATCH (e:Entity) RETURN e` |
| Match with property | `({prop: value})` | `MATCH (e {name: "OpenAI"}) RETURN e` |
| Create node | `CREATE (n:Label {...})` | `CREATE (e:Entity {name: "Test"})` |
| Create relationship | `CREATE (a)-[:TYPE]->(b)` | `CREATE (a)-[:KNOWS]->(b)` |
| Filter results | `WHERE` | `WHERE e.name CONTAINS "AI"` |
| Return properties | `RETURN n.prop` | `RETURN e.name, e.summary` |
| Count | `count()` | `RETURN count(n)` |
| Sort | `ORDER BY` | `ORDER BY e.name DESC` |
| Limit results | `LIMIT n` | `LIMIT 10` |
| Variable-length path | `-[:TYPE*min..max]-` | `-[:RELATES_TO*1..3]-` |
| Aggregate | `collect()`, `count()`, `avg()` | `RETURN collect(e.name)` |

---

## 🎓 Resources for Learning More

### Official Neo4j Resources
- **Neo4j Browser Guide**: Type `:play intro` in Neo4j Browser
- **Cypher Manual**: https://neo4j.com/docs/cypher-manual/current/
- **GraphAcademy**: https://graphacademy.neo4j.com/ (Free courses!)

### Practice Queries
1. Start with `MATCH (n) RETURN n LIMIT 10`
2. Progressively add filters with `WHERE`
3. Join patterns with relationships
4. Experiment with aggregations
5. Try path queries

### Neo4j Browser Features
- **Auto-complete**: Start typing and press Ctrl+Space
- **History**: Click clock icon for query history
- **Favorites**: Star icon to save queries
- **Download results**: Export as CSV/JSON
- **Graph visualization settings**: Gear icon at bottom

---

## 💡 Tips for Your RAG System

1. **Exploring Knowledge**: Start with entity-centric queries to understand what's in your graph
2. **Context Retrieval**: Use 1-2 hop queries to get relevant context around entities
3. **Graph Traversal**: Use `[:RELATES_TO*1..3]` to expand knowledge for RAG responses
4. **Hybrid Search**: Combine vector similarity (from PostgreSQL) with graph context (from Neo4j)

---

## ⚡ Quick Reference Commands

```cypher
// See all node types
CALL db.labels()

// See all relationship types
CALL db.relationshipTypes()

// See database schema
CALL db.schema.visualization()

// Count everything
MATCH (n) RETURN count(n)

// Clear entire database (⚠️ CAREFUL!)
MATCH (n) DETACH DELETE n
```

---

Happy graphing! 🚀 Start with simple `MATCH` queries and gradually build complexity. The Neo4j Browser's visual feedback makes learning intuitive.
