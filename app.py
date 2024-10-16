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
from lemme import do_search, insert_markup

# from typing_extensions import Literal
COMMAND_LIST = 0
COMMAND_SEARCH = 1
COMMAND_ARTICLE = 2


def cmd_list(data: dict) -> dict:
    medicine_list = internal.read_db(
        "list_by_catID.sql",
        {"category_id": data["params"]["value"]},
    )
    html = render_template(
        "category_list.html",
        count=len(medicine_list),
        medicine_list=medicine_list,
    )
    data["dom"].append(
        {
            "selector": "#content",
            "html": html,
            "attr_set": [
                ["data-lemmas", json.dumps([])],
            ],
        }
    )
    return data


def cmd_article(data: dict, input_data) -> dict:
    print(data)

    # находим родительский артикль
    main_id = [data["params"]["value"]]
    while True:
        tmp = internal.read_db("article_work/get_parent.sql", {"id": main_id})
        if len(tmp) == 0:
            break
        tmp = tmp[0]["parent"]
        if tmp is None:
            break
        main_id = tmp

    # теперь в ID у нас родительский, читаем всю статью
    articles = []

    headers = internal.read_db(
        "article_work/get_child.sql", {"parent": main_id}
    )
    for h in headers:
        h["paragraphs"] = []
        paragraphs = internal.read_db(
            "article_work/get_child.sql",
            {"parent": h["id"]},
        )
        for p in paragraphs:
            h["paragraphs"].append(p)
        articles.append(h)

    data["dom"].append(
        {
            "selector": "#content",
            "html": render_template("article.html", articles=articles),
            "attr_set": [
                ["data-articleid", main_id],
            ],
        },
    )
    # data["attr"]["set"].append()
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
                ["data-lemmas", json.dumps(used_lemmas)],
            ],
        }
    )
    return data


@app.route("/")
def main():
    categories = internal.read_db("categories_list.sql")
    return render_template("main.html", categories=categories)


@app.route("/parse_data", methods=["POST"])
def parse_data():

    input_data = json.loads(request.get_data())
    result = {
        "dom": [],
        "storage": {},
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
