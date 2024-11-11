from internal import app, flask_db_conn
import internal, os, io, traceback, json
from werkzeug.exceptions import HTTPException
from flask import (
    Flask,
    jsonify,
    request,
    session,
    render_template,
)
from lemme import do_search, insert_markup, HTML_TAGS

# from typing_extensions import Literal
COMMAND_LIST = 0
COMMAND_SEARCH = 1
COMMAND_ARTICLE = 2
SITE_TITLE = "Мозгоправ"
KEY_ARTICLE = "HEADERS"


def cmd_list(data: dict) -> dict:
    cat_id = data["params"]["value"]
    if cat_id >= 0:  # for category details

        category_name = internal.read_db(
            sql_filename="cat/category_name.sql",
            params={"category_id": cat_id},
        )[0]
        medicine_list = internal.read_db(
            sql_filename="cat/medicine_list.sql",
            params={"category_id": cat_id},
        )
        html = render_template(
            "medicine_list.html",
            category_name=category_name,
            count=len(medicine_list),
            docs=medicine_list,
        )
    else:
        # for category list
        categories_list = internal.read_db(
            sql_filename="cat/cat_count.sql",
        )
        html = render_template(
            "categories_list.html",
            categories_list=categories_list,
        )
    data["dom"].append(
        {
            "selector": "#content",
            "html": html,
            "attr_set": [
                {
                    "attr": "data-lemmas",
                    "value": json.dumps([]),
                }
            ],
        }
    )

    data["dom"].append(
        {
            "selector": "title",
            "html": f"{SITE_TITLE} :: список категорий",
        }
    )
    return data


def cmd_article(data: dict, input_data) -> dict:
    # print(data)
    # наличие input_data['params'] означает что мы пришли из поиска
    # подсвечиваем леммы
    # также передаем в ответе номер артикля, который нам нужно открыть

    # находим родительский артикль
    path = [data["params"]["value"]]
    while True:
        parent = internal.read_db(
            sql_filename="article_work/get_parent.sql",
            params={"id": path[0]},
        )
        if len(parent) == 0:
            break
        parent = parent[0]["parent"]
        if parent is None:
            break
        path.insert(0, parent)

    # если заголовок или параграф
    # то открываем в бразуере этот заголовок
    # и записываем в localstorage этот открытый параграф
    if len(path) >= 2:
        data["storage"].append({"key": KEY_ARTICLE, "value": {path[0]: [path[1]]}, "action": 0})
        data["params"]["scroll"] = path[1]

    # теперь в path[0] у нас родительский ID, читаем всю статью
    headers = internal.read_db(
        sql_filename="article_work/get_child.sql",
        params={"parent": [path[0]]},
    )
    doc_name = internal.read_db(
        sql_filename="article_work/get_article.sql",
        params={"id": path[0]},
    )[0]

    # в texts у нас чистые тексты, в tree соответсвие параграфам заголовков
    texts, tree = {}, {}
    for h in headers:
        texts[h["id"]] = h["txt"]
        tree[h["id"]] = []

    paragraphs = internal.read_db(
        sql_filename="article_work/get_child.sql",
        params={"parent": list(tree)},
    )

    # сливаем все тексты (параграфы и статьи) в один массив
    # заодно делаем дерево, какая статья какому параграфу
    for p in paragraphs:
        texts[p["id"]] = p["txt"]
        tree[p["parent"]].append(p["id"])

    if "params" in input_data:  # находим все использования лемм
        used_lemmas = json.loads(input_data["params"])
        used_lemmas = internal.read_db(
            sql_filename="article_work/get_used_lemmas.sql",
            params={"articles_list": list(texts), "lemmas_list": used_lemmas},
        )
        used_articles = set(item["article_id"] for item in used_lemmas)
        for id in used_articles:
            markup = [(x["start"], x["len"]) for x in used_lemmas if x["article_id"] == id]
            texts[id] = insert_markup(texts[id], markup, HTML_TAGS)
            # print(id, texts[id])
        pass

    data["dom"].append(
        {
            "selector": "#content",
            "html": render_template("article.html", tree=tree, texts=texts, doc=doc_name["txt"]),
            "attr_set": [
                {
                    "attr": "data-docid",
                    "value": path[0],
                }
            ],
        },
    )
    data["dom"].append(
        {
            "selector": "title",
            "html": f"{SITE_TITLE} :: {doc_name['txt']}",
        }
    )
    # print(data)
    return data


def cmd_search(data: dict) -> dict:
    sr = do_search(data["params"]["value"])
    html = render_template(
        "search.html",
        search_info=sr["search_info"],
        search_result=sr["search_result"],
    )

    # сразу сохраняем используемые ID лемм
    used_lemmas = []
    for l in sr["needle"]:
        used_lemmas.append(l["dict_index"])
    data["dom"].append(
        {
            "selector": "#content",
            "html": html,
            "attr_set": [
                {
                    "attr": "data-lemmas",
                    "value": json.dumps(used_lemmas),
                }
            ],
        }
    )

    # добавляем титул страницы
    data["dom"].append(
        {
            "selector": "title",
            "html": f"{SITE_TITLE} :: результаты поиска",
        }
    )
    return data


@app.route("/")
def main():
    # categories = internal.read_db("categories_list.sql")
    # return render_template("main.html", categories=categories)
    return render_template(
        "main.html",
    )


@app.route("/parse_data", methods=["POST"])
def parse_data():

    input_data = json.loads(request.get_data())
    # print(input_data)
    result = {
        "dom": [],
        "storage": [],
        "params": {
            "command": input_data["command"],
            "value": input_data["value"],
        },
    }

    if input_data["command"] == COMMAND_LIST:
        result = cmd_list(result)

    elif input_data["command"] == COMMAND_SEARCH:
        result = cmd_search(result)

    elif input_data["command"] == COMMAND_ARTICLE:
        result = cmd_article(result, input_data)

    return jsonify(result)


# {'dom': [], 'data': {}, 'params': {'command': 2, 'value': 106}}


def main():
    # conn = sqlite3.connect("C:\\drug_site\\drugs.db")
    # conn.row_factory = make_dicts
    # conn.set_trace_callback(sqlite_trace_callback)
    d = {
        "dom": [],
        "data": {},
        "params": {"command": 2, "value": 14},
    }
    d = cmd_article(d)
    print(d)


if __name__ == "__main__":
    main()
