from internal import app
import internal, os, io, traceback, json
from werkzeug.exceptions import HTTPException
from flask import Flask, jsonify, request, session, render_template

COMMAND_LIST = 0
COMMAND_SEARCH = 1
COMMAND_ARTICLE = 2


@app.route("/")
def main():
    categories = internal.read_db("categories_list.sql")
    categories.insert(0, {"category_id": 0, "category_name": "полный список"})
    return render_template("main.html", categories=categories)


@app.route("/parse_data", methods=["POST"])
def parse_data():

    data = json.loads(request.get_data())
    command = data["command"]
    value = data["value"]
    result = {"dom": [], "data": {}, "params": {"command": command, "value": value}}
    if command == COMMAND_LIST:
        medicine_list = internal.read_db("list_by_catID.sql", {"category_id": value})
        html = render_template("category_list.html", count=len(medicine_list), medicine_list=medicine_list)
        result["dom"].append({"selector": "#content", "html": html})

    elif command == COMMAND_SEARCH:
        result["dom"].append({"selector": "#content", "html": f"SEARCH = { value}"})

    elif command == COMMAND_ARTICLE:
        tmp_article = internal.read_db("get_article.sql", {"medicine_id": value})
        article = []
        for p in tmp_article:
            if p["is_header"]:
                article.append({"header": p["article_text"], "text": []})
            else:
                if len(article) == 0:
                    continue
                article[-1]["text"].append(p["article_text"])
        result["dom"].append({"selector": "#content", "html": render_template("article.html", article=article, medicine_id=data["value"])})

    return jsonify(result)
