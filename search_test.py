import os
from pathlib import Path
from whoosh.fields import Schema, TEXT, ID
from whoosh import index
from whoosh.qparser import QueryParser

current_dir = os.path.dirname(os.path.realpath(__file__))
# index


if not os.path.exists(index_dir):
        os.mkdir(index_dir)

    schema = Schema(id=ID(stored=True), title=TEXT(stored=True), content=TEXT(stored=True))

    ix = index.create_in(index_dir, schema)

    writer = ix.writer()


    with ix.searcher() as searcher:
        query = QueryParser("content", ix.schema).parse("hello world")
        results = searcher.search(query, terms=True)

        for r in results:
            print(r, r.score)
            # Was this results object created with terms=True?
            if results.has_matched_terms():
                # What terms matched in the results?
                print(results.matched_terms())

        # What terms matched in each hit?
        print("matched terms")
        for hit in results:
            print(hit.matched_terms())
