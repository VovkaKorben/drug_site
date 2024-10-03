import sqlite3
import io
import traceback
import os
import re
from pathlib import Path


def make_dicts(cursor, row):
    return dict((cursor.description[idx][0], value) for idx, value in enumerate(row))


try:
    current_dir = os.path.dirname(os.path.realpath(__file__))
    articles_path = os.path.join(current_dir, "articles")
    file_names = [f for f in os.listdir(articles_path)]
    print(f"Найдено файлов: {len(file_names)}")

    conn = sqlite3.connect("drugs.db")
    conn.row_factory = make_dicts

    cursor = conn.execute(f"PRAGMA foreign_keys = false;")
    conn.commit()

    for table_name in ["articles", "medicines", "medicine_categories"]:
        cursor = conn.execute(f"delete from {table_name}")
        conn.commit()
   
    for filename in file_names:

        with open(os.path.join(articles_path, filename), "r", encoding="UTF-8") as article_file:
            article_text = article_file.read()

        cur = conn.execute("select IFNULL(max(medicine_id),-1) as medicine_id from medicines")
        medicine_id = cur.fetchall()
        cur.close()
        medicine_id = medicine_id[0]["medicine_id"]
        medicine_id += 1
        print(f"[id:{medicine_id}] {filename}...", end="")

        medicine_name = Path(filename).stem.strip()
        cursor = conn.execute(f"INSERT into medicines (medicine_id,medicine_name) VALUES ({medicine_id},'{medicine_name}')")
        conn.commit()

        order_no = 0
        headers_count, para_count = 0, 0

        matches = re.finditer(r"<(?P<tag>\w+)>(?P<value>.*?)<\/(?P=tag)>", article_text, re.I | re.DOTALL)
        for match in matches:
            tag = match.group(1).upper()
            text = match.group(2)
            if tag == "Q":
                text = int(text)
                cursor = conn.execute(f"INSERT into medicine_categories (medicine_id,category_id) VALUES ({medicine_id},{text})")
                conn.commit()
            if tag == "H1":
                is_header = 1
                headers_count += 1
            elif tag == "P":
                is_header = 0
                para_count += 1
            else:
                continue
            cursor = conn.execute(f"INSERT into articles (medicine_id,order_no,is_header,article_text) VALUES ({medicine_id},{order_no},{is_header},'{text}')")
            conn.commit()
            order_no += 1
        print(f"Заголовков: {headers_count}, параграфов:{para_count}")
finally:
    cursor = conn.execute(f"PRAGMA foreign_keys = true;")
    conn.commit()

    if conn:
        conn.close()
