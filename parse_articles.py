import sqlite3
import os
import re
from pathlib import Path
import lemme
import sys
from glob import glob


# ARTICLE_DIR = "art3"
ARTICLE_DIR = "C:\\drug_site\\articles"


def make_dicts(cursor, row):
    return dict(
        (cursor.description[idx][0], value) for idx, value in enumerate(row)
    )


def put_articles(path: str, conn):
    file_names = [
        y
        for x in os.walk(ARTICLE_DIR)
        for y in glob(os.path.join(x[0], "*.txt"))
    ]
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
            conn.execute(
                "INSERT into articles (id,parent,txt) VALUES (?,?,?);",
                (medicine_id, None, medicine_name),
            )

            conn.commit()

            # id = medicine_id + 1

            with open(
                os.path.join(path, filename), "r", encoding="UTF-8"
            ) as article_file:
                article_text = article_file.read()

            print(f"[id:{medicine_id}] {filename}...", end="")

            headers_count, para_count = 0, 0

            matches = re.finditer(
                r"<(?P<tag>p|h1|q)>(?P<value>.*?)<\/(?P=tag)>",
                article_text,
                re.I | re.DOTALL,
            )
            for match in matches:
                tag = match.group(1).upper()
                text = match.group(2)
                if tag == "Q":
                    text = int(text)
                    conn.execute(
                        "INSERT into medicine_categories (medicine_id,category_id) VALUES (?,?)",
                        (medicine_id, text),
                    )
                    conn.commit()
                if tag == "H1":
                    id += 1
                    conn.execute(
                        "INSERT into articles (id,parent,txt) VALUES (?,?,?);",
                        (id, medicine_id, text),
                    )
                    conn.commit()
                    header_id = id

                    headers_count += 1
                elif tag == "P":
                    id += 1
                    conn.execute(
                        "INSERT INTO articles (id, parent, txt) VALUES (?, ?, ?)",
                        (id, header_id, text),
                    )

                    conn.commit()
                    para_count += 1
                else:
                    continue
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
        for l in lemmas:
            cur = conn.execute(
                "select id from lemmas where lemma = ?;", (l["morphem"],)
            )
            qres = cur.fetchall()
            if len(qres) == 0:  # добавляем слово
                cur = conn.execute(
                    "select ifnull(max(id),-1) max_id from lemmas;"
                )
                qres = cur.fetchall()
                lemma_id = qres[0]["max_id"] + 1
                conn.execute(
                    "insert into lemmas (id,lemma) values (?,?);",
                    (lemma_id, l["morphem"]),
                )
            else:
                lemma_id = qres[0]["id"]
            conn.execute(
                "insert into lemmas_usage (lemma_id,article_id,start,len,word_index) values (?,?,?,?,?);",
                (lemma_id, article_id, l["start"], l["len"], l["word_index"]),
            )
            conn.commit()
        conn.execute(
            "update articles set ('word_count')=(?) where id=?;",
            (len(lemmas), article_id),
        )
        conn.commit()

    cur = conn.execute("select * from articles")
    try:
        while True:
            a = cur.fetchone()
            if a is None:
                break
            sys.stdout.write(f'\rTokenize: {a["id"]+1}')
            sys.stdout.flush()
            tokenize_article(a["id"], a["txt"])
    finally:
        cur.close()


"""
    cur = conn.execute("select * from articles")
    try:
        while True:
            a = cur.fetchone()
            if a is None:
                break
            # print(a)def tokenize_word(word:str)->str:
            if len(lemma)>1 and len(word)>1 and word not in disallowed_words and lemma not in disallowed_words:
        def add_word(word:str)->int:
            lemma = tokenize_word(word)
            
            lemma = morph.parse(word)[0].normal_form.upper()
            if len(lemma)>1 and len(word)>1 and word not in disallowed_words and lemma not in disallowed_words:
                lemma = morph.parse(word)[0].normal_form.upper()
                # проверяем, есть ли слово в базе
                cur = conn.execute(f"select id from lemmas where lemma = '{lemma}';")
                qres = cur.fetchall()
                if len(qres)==0: # добавляем слово
                    cur = conn.execute(f"select ifnull(max(id),-1) max_id from lemmas;")
                    qres = cur.fetchall()
                    id = qres[0]['max_id'] + 1
                    conn.execute(f"insert into lemmas (id,lemma) values ({id},'{lemma}');")  
                else:
                    id = qres[0]['id']
                conn.execute(f"insert into lemmas_usage (lemma_id,article_id,start) values ({id},{aritcle_id},{start});")  
                conn.commit()
"""
# def add_usage

# r.append({'word':aritcle_text[start:pos],'lemma':lemma,'start':start,'end':pos})


# finally:
#     cur.close()


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
