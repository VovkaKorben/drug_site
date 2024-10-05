import os
from pathlib import Path
from whoosh.fields import Schema, TEXT, ID
from whoosh import index
from whoosh.qparser import QueryParser
from whoosh.index import open_dir
from whoosh.qparser import QueryParser
from whoosh import qparser, query

current_dir = os.path.dirname(os.path.realpath(__file__))
index_dir = os.path.join(current_dir, "index")
ix = open_dir(index_dir)
print(ix.schema)

with ix.searcher() as searcher:
    # print(list(searcher.lexicon("text")))
    qp = qparser.QueryParser("article", schema=ix.schema, termclass=query.Variations)
    # qp = QueryParser("article", schema=ix.schema)
    q = qp.parse("ЭФФЕКТЫ")
    results = searcher.search(q)
    print(f"Total: {len(results)} results")
    for hit in results:
        print(f'{hit["id"]}\t\t{hit.score}\t\t{hit.highlights("article")}')
