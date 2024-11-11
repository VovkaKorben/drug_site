import sqlite3
import os
import re
from pathlib import Path
import lemme
import sys
from glob import glob
from internal import read_db, make_dicts

ARTICLE_DIR = "art_ok"


# def make_dicts(cursor, row):    return dict((cursor.description[idx][0], value) for idx, value in enumerate(row))


def put_articles(path: str, conn):
    file_names = [y for x in os.walk(path) for y in glob(os.path.join(x[0], "*.*"))]
    # file_names = [f for f in os.listdir(path)]
    print(f"Найдено файлов: {len(file_names)}")

    conn.execute(f"PRAGMA foreign_keys = false;")
    conn.commit()

    id = 0
    header_id = None
    try:
        for filename in file_names:
            medicine_id = id
            medicine_name = Path(filename).stem.strip()
            read_db(
                sql_query="INSERT into articles (id,parent,txt) VALUES (:medicine_id,NULL,:medicine_name);",
                params={"medicine_id": medicine_id, "medicine_name": medicine_name},
                result_required=False,
                conn=conn,
            )

            conn.commit()

            # id = medicine_id + 1

            with open(os.path.join(path, filename), "r", encoding="UTF-8") as article_file:
                article_text = article_file.read()

                article_text = article_text.replace("\n", "")

                print(f"[id:{medicine_id}] {filename}...", end="")

                headers_count, para_count = 0, 0
                category_collect = []

                matches = re.finditer(
                    r"<(?P<tag>p|h1|q)>(?P<value>.*?)<\/(?P=tag)>",
                    article_text,
                    re.I | re.DOTALL,
                )
                for match in matches:
                    tag = match.group(1).upper()
                    text = match.group(2)
                    if tag == "Q":
                        cat = int(text)
                        category_collect.append(cat)

                    if tag == "H1":
                        id += 1
                        read_db(
                            sql_query="INSERT into articles (id,parent,txt) VALUES (:id,:medicine_id,:text);",
                            params={"id": id, "medicine_id": medicine_id, "text": text},
                            result_required=False,
                            conn=conn,
                        )
                        conn.commit()
                        header_id = id

                        headers_count += 1
                    elif tag == "P":
                        id += 1
                        read_db(
                            sql_query="INSERT INTO articles (id, parent, txt) VALUES (:id, :header_id, :text)",
                            params={"id": id, "header_id": header_id, "text": text},
                            result_required=False,
                            conn=conn,
                        )

                        conn.commit()
                        para_count += 1
                    else:
                        continue

            # если категорий не было - автоматически в другие
            if len(category_collect) == 0:
                category_collect = [7]
            for cat in category_collect:
                read_db(
                    sql_query="INSERT into medicine_categories (medicine_id,category_id) VALUES (:medicine_id,:cat)",
                    params={"medicine_id": medicine_id, "cat": cat},
                    result_required=False,
                    conn=conn,
                )
            conn.commit()

            print(f"Заголовков: {headers_count}, параграфов:{para_count}")
            id += 1
    finally:
        conn.execute(f"PRAGMA foreign_keys = true;")
        conn.commit()
    return id


def make_index(conn):

    def tokenize_article(article_id, line):
        lemmas = lemme.tokenize_string(line)
        # проверяем, есть ли слово в базе
        for l_no in range(len(lemmas)):
            qres = read_db(
                sql_query="select id from lemmas where lemma = :w;",
                params={"w": lemmas[l_no]["morphem"]},
                conn=conn,
            )
            if len(qres) == 0:  # добавляем слово
                qres = read_db(
                    sql_query="select ifnull(max(id),-1) max_id from lemmas;",
                    conn=conn,
                )
                lemma_id = qres[0]["max_id"] + 1
                read_db(
                    sql_query="insert into lemmas (id,lemma) values (:id,:w);",
                    params={"id": lemma_id, "w": lemmas[l_no]["morphem"]},
                    result_required=False,
                    conn=conn,
                )
            else:
                lemma_id = qres[0]["id"]

            read_db(
                sql_query="insert into lemmas_usage (lemma_id,article_id,start,len,word_index) values (:lemma_id,:article_id,:start,:len,:word_index);",
                params={
                    "lemma_id": lemma_id,
                    "article_id": article_id,
                    "start": lemmas[l_no]["start"],
                    "len": lemmas[l_no]["len"],
                    "word_index": l_no,
                },
                result_required=False,
                conn=conn,
            )
            conn.commit()
        read_db(
            sql_query="update articles set ('word_count')=(:len) where id=:article_id;",
            params={"len": len(lemmas), "article_id": article_id},
            result_required=False,
            conn=conn,
        )
        conn.commit()

    cur = read_db(
        sql_query="select * from articles",
        conn=conn,
    )
    for a in cur:
        sys.stdout.write(f'\rTokenize: {a["id"]+1}')
        sys.stdout.flush()
        tokenize_article(a["id"], a["txt"])


try:
    conn = sqlite3.connect("drugs.db")
    conn.row_factory = make_dicts

    # truncate tables
    for table_name in [
        "articles",
        "medicines",
        "medicine_categories",
        "lemmas",
        "lemmas_usage",
    ]:
        conn.execute(f"delete from {table_name};")
        conn.commit()

    current_dir = os.path.dirname(os.path.realpath(__file__))
    count = put_articles(os.path.join(current_dir, ARTICLE_DIR), conn)
    print(f"Records: {count}")
    # index
    make_index(conn)

finally:

    if conn:
        conn.close()
