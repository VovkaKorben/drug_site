import sqlite3
import os
import re
from pathlib import Path
from whoosh.fields import Schema, TEXT, ID
from whoosh import index
from whoosh.qparser import QueryParser


def make_dicts(cursor, row):
    return dict((cursor.description[idx][0], value) for idx, value in enumerate(row))


def put_articles(path: str, dbconn):

    file_names = [f for f in os.listdir(path)]
    print(f"Найдено файлов: {len(file_names)}")

    cursor = dbconn.execute(f"PRAGMA foreign_keys = false;")
    dbconn.commit()
    try:

        for table_name in ["articles", "medicines", "medicine_categories"]:
            cursor = dbconn.execute(f"delete from {table_name}")
            dbconn.commit()

        for filename in file_names:

            with open(os.path.join(path, filename), "r", encoding="UTF-8") as article_file:
                article_text = article_file.read()

            cur = dbconn.execute("select IFNULL(max(medicine_id),-1) as medicine_id from medicines")
            medicine_id = cur.fetchall()
            cur.close()
            medicine_id = medicine_id[0]["medicine_id"]
            medicine_id += 1
            print(f"[id:{medicine_id}] {filename}...", end="")

            medicine_name = Path(filename).stem.strip()
            cursor = dbconn.execute(f"INSERT into medicines (medicine_id,medicine_name) VALUES ({medicine_id},'{medicine_name}')")
            dbconn.commit()

            order_no = 0
            headers_count, para_count = 0, 0

            matches = re.finditer(r"<(?P<tag>\w+)>(?P<value>.*?)<\/(?P=tag)>", article_text, re.I | re.DOTALL)
            for match in matches:
                tag = match.group(1).upper()
                text = match.group(2)
                if tag == "Q":
                    text = int(text)
                    cursor = dbconn.execute(f"INSERT into medicine_categories (medicine_id,category_id) VALUES ({medicine_id},{text})")
                    dbconn.commit()
                if tag == "H1":
                    is_header = 1
                    headers_count += 1
                elif tag == "P":
                    is_header = 0
                    para_count += 1
                else:
                    continue
                cursor = dbconn.execute(f"INSERT into articles (medicine_id,order_no,is_header,article_text) VALUES ({medicine_id},{order_no},{is_header},'{text}')")
                dbconn.commit()
                order_no += 1
            print(f"Заголовков: {headers_count}, параграфов:{para_count}")
    finally:
        cursor = conn.execute(f"PRAGMA foreign_keys = true;")
        dbconn.commit()


def make_index(index_dir, conn):
    if not os.path.exists(index_dir):
        os.mkdir(index_dir)

    schema = Schema(id=ID(stored=True), title=TEXT(stored=True), content=TEXT(stored=True))
    # schema = Schema(title=TEXT(stored=True), path=ID(stored=True), content=TEXT(stored=True))

    ix = index.create_in(index_dir, schema)

    writer = ix.writer()

    prev_id = -1
    started, title, content = False, "", ""
    cur = conn.execute("select * from articles order by medicine_id, order_no")
    while True:
        a = cur.fetchone()
        if a is None:
            break
        print(a)
        if prev_id != a["medicine_id"]:
            print(f"NEW ARTICLE ({a['medicine_id']})")
            if started:
                print("PUSH PREV")
                writer.add_document(title=title, content=content, id=str(prev_id))
                started, title, content = False, "", ""
            prev_id = a["medicine_id"]

        if a["is_header"]:
            if started:
                print("PUSH PREV")
                writer.add_document(title=title, content=content, id=str(prev_id))
                started, title, content = False, "", ""
            print("SET HEADER")
            started, title = True, a["article_text"]
        else:
            print("ADD PARA")
            started = True
            content += a["article_text"]
    if started:
        print("PUSH PREV")
        writer.add_document(title=title, content=content, id=str(prev_id))
    writer.commit()
    cur.close()

    # writer.add_document(title="My document", content="This is my python document! hello big world", path="/a")
    # writer.add_document(title="Second try", content="This is the second example hello world.", path="/b")
    # writer.add_document(title="Third time's the charm", content="More examples. Examples are many.", path="/c")

    # writer.commit()

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


try:
    conn = sqlite3.connect("drugs.db")
    conn.row_factory = make_dicts
    current_dir = os.path.dirname(os.path.realpath(__file__))
    put_articles(os.path.join(current_dir, "articles"), conn)
    # index
    make_index(os.path.join(current_dir, "index"), conn)

finally:

    if conn:
        conn.close()
