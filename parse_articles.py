import sqlite3
import os
import re
from pathlib import Path
import pymorphy2
"""
from whoosh.fields import Schema, TEXT, ID
from whoosh import index
from whoosh.qparser import QueryParser
from whoosh.analysis import StemmingAnalyzer
from whoosh.index import create_in
from whoosh.fields import Schema, TEXT, ID
from whoosh.qparser import QueryParser
from whoosh.analysis import RegexTokenizer, Filter
from whoosh import fields
from whoosh.analysis import StemmingAnalyzer
"""


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


def put_articles(path: str, conn):

    file_names = [f for f in os.listdir(path)]
    print(f"Найдено файлов: {len(file_names)}")

    conn.execute(f"PRAGMA foreign_keys = false;")
    conn.commit()

   
    id = 0
    header_id = None
    try:
        for filename in file_names:
            medicine_id = id
            medicine_name = Path(filename).stem.strip()
            conn.execute(f"INSERT into articles (id,parent,txt) VALUES ({medicine_id},{'null'},'{medicine_name}')")
            conn.commit()

            # id = medicine_id + 1

            with open(os.path.join(path, filename), "r", encoding="UTF-8") as article_file:
                article_text = article_file.read()
           
            print(f"[id:{medicine_id}] {filename}...", end="")

            headers_count, para_count = 0, 0

            matches = re.finditer(r"<(?P<tag>p|h1|q)>(?P<value>.*?)<\/(?P=tag)>", article_text, re.I | re.DOTALL)
            for match in matches:
                tag = match.group(1).upper()
                text = match.group(2)
                if tag == "Q":
                    text = int(text)
                    conn.execute(f"INSERT into medicine_categories (medicine_id,category_id) VALUES ({medicine_id},{text})")
                    conn.commit()
                if tag == "H1":
                    id += 1
                    conn.execute(f"INSERT into articles (id,parent,txt) VALUES ({id},{medicine_id},'{text}')")
                    conn.commit()
                    header_id = id

                    headers_count += 1
                elif tag == "P":
                    id += 1
                    conn.execute(f"INSERT into articles (id,parent,txt) VALUES ({id},{header_id},'{text}')")
                    conn.commit()
                    para_count += 1
                else:
                    continue
            print(f"Заголовков: {headers_count}, параграфов:{para_count}")
            id += 1
    finally:
        conn.execute(f"PRAGMA foreign_keys = true;")
        conn.commit()


def make_index(index_dir, conn):
    
    
    LEVENSTAIN_TRESHOLD = 0.1

    def tokenize_string(aritcle_id:int,aritcle_text:str)->dict:
        def add_word(w:str):
            bw = ['А','В','ТАК','КАК','ГДЕ','И','О','НЕ','ПРИ','С','ТАКЖЕ','ЖЕ','ПО','ЧТО','ПОД','НАД','БЕЗ','ВО','НА','ИЛИ']
            if w not in bw:
                lemma = morph.parse(w)[0].normal_form.upper()
                r.append({'word':text[start:pos],'lemma':lemma,'start':start,'end':pos})
                

        ab = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЬЫЪЭЮЯ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        
        text = text.upper()
        text_len = len(text)
        pos = 0
        start = None
        
        r = []
        while pos<text_len:
            if text[pos] in ab:
                if start is None:
                    start = pos
            else:
                if start is not None:
                    add_word( text[start:pos])
                    start = None

            pos += 1
        # check if line ends with word
        if start is not None:
            add_word(text[start:text_len])
        return r








    cur = conn.execute("select * from articles")
    try:
        while True:
            a = cur.fetchone()
            if a is None:
                break
            # print(a)
            tokenize_string(a["id"], article=a["txt"])
    finally:
        cur.close()


try:
    conn = sqlite3.connect("drugs.db")
    conn.row_factory = make_dicts

    # truncate tables
    for table_name in ["articles", "medicines", "medicine_categories",'lemmas','lemmas_usage']:
        conn.execute(f"delete from {table_name}")
        conn.commit()



    current_dir = os.path.dirname(os.path.realpath(__file__))
    put_articles(os.path.join(current_dir, "articles"), conn)
    # index
    make_index(os.path.join(current_dir, "index"), conn)

finally:

    if conn:
        conn.close()
