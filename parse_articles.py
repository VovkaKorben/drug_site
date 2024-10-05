import sqlite3
import os
import re
from pathlib import Path
from whoosh.fields import Schema, TEXT, ID
from whoosh import index
from whoosh.qparser import QueryParser
from whoosh.analysis import StemmingAnalyzer
from whoosh.index import create_in
from whoosh.fields import Schema, TEXT, ID
from whoosh.qparser import QueryParser
from whoosh.analysis import RegexTokenizer, Filter
import pymorphy2
from whoosh import fields
from whoosh.analysis import StemmingAnalyzer

"""
# Создаем морфологический анализатор
morph = pymorphy2.MorphAnalyzer()


# Класс фильтра для лемматизации
class LemmatizerFilter(Filter):
    def __call__(self, tokens):
        for token in tokens:
            token.text = morph.parse(token.text)[0].normal_form
            yield token
"""


def make_dicts(cursor, row):
    return dict((cursor.description[idx][0], value) for idx, value in enumerate(row))


def put_articles(path: str, dbconn):

    file_names = [f for f in os.listdir(path)]
    print(f"Найдено файлов: {len(file_names)}")

    cursor = dbconn.execute(f"PRAGMA foreign_keys = false;")
    dbconn.commit()

    """
    cur = dbconn.execute("select IFNULL(max(medicine_id),-1) as medicine_id from articles")
    medicine_id = cur.fetchall()
    cur.close()
    medicine_id = medicine_id[0]["medicine_id"]
    medicine_id += 1
    """
    id = 0
    header_id = None
    try:

        # truncate tables
        for table_name in ["articles", "medicines", "medicine_categories"]:
            dbconn.execute(f"delete from {table_name}")
            dbconn.commit()

        for filename in file_names:
            medicine_id = id
            medicine_name = Path(filename).stem.strip()
            dbconn.execute(f"INSERT into articles (id,parent,txt) VALUES ({medicine_id},{'null'},'{medicine_name}')")
            dbconn.commit()

            # id = medicine_id + 1

            with open(os.path.join(path, filename), "r", encoding="UTF-8") as article_file:
                article_text = article_file.read()

            """
            cur = dbconn.execute("select IFNULL(max(medicine_id),-1) as medicine_id from medicines")
            medicine_id = cur.fetchall()
            cur.close()
            medicine_id = medicine_id[0]["medicine_id"]
            medicine_id += 1
            """
            print(f"[id:{medicine_id}] {filename}...", end="")

            headers_count, para_count = 0, 0

            # matches = re.finditer(r"<(?P<tag>\w+)>(?P<value>.*?)<\/(?P=tag)>", article_text, re.I | re.DOTALL)
            matches = re.finditer(r"<(?P<tag>p|h1|q)>(?P<value>.*?)<\/(?P=tag)>", article_text, re.I | re.DOTALL)
            for match in matches:
                tag = match.group(1).upper()
                text = match.group(2)
                if tag == "Q":
                    text = int(text)
                    dbconn.execute(f"INSERT into medicine_categories (medicine_id,category_id) VALUES ({medicine_id},{text})")
                    dbconn.commit()
                if tag == "H1":
                    id += 1
                    dbconn.execute(f"INSERT into articles (id,parent,txt) VALUES ({id},{medicine_id},'{text}')")
                    dbconn.commit()
                    header_id = id

                    headers_count += 1
                elif tag == "P":
                    id += 1
                    dbconn.execute(f"INSERT into articles (id,parent,txt) VALUES ({id},{header_id},'{text}')")
                    dbconn.commit()
                    para_count += 1
                else:
                    continue
            print(f"Заголовков: {headers_count}, параграфов:{para_count}")
            id += 1
    finally:
        cursor = conn.execute(f"PRAGMA foreign_keys = true;")
        dbconn.commit()


def make_index(index_dir, conn):
    if not os.path.exists(index_dir):
        os.mkdir(index_dir)
    # lemmatizer = RegexTokenizer() | LemmatizerFilter()

    stem_ana = StemmingAnalyzer()
    schema = Schema(id=ID(stored=True), article=TEXT(stored=True, analyzer=stem_ana))
    ix = index.create_in(index_dir, schema)

    writer = ix.writer()
    try:
        cur = conn.execute("select * from articles")
        try:
            while True:
                a = cur.fetchone()
                if a is None:
                    break
                # print(a)
                writer.add_document(id=str(a["id"]), article=a["txt"])
        finally:
            cur.close()
    finally:
        writer.commit()


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
