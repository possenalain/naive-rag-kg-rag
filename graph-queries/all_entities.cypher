MATCH (e:Entity)-[r:RELATES_TO]-(e2)
RETURN e, r, e2