from internal import app, db_conn
import internal, os, io, traceback, json
from werkzeug.exceptions import HTTPException
from flask import Flask, jsonify, request, session, render_template
from lemme import do_search,insert_markup
COMMAND_LIST = 0
COMMAND_SEARCH = 1
COMMAND_ARTICLE = 2


def cmd_list(data: dict) -> dict:
    medicine_list = internal.read_db("list_by_catID.sql", {"category_id": data["params"]["value"]})
    html = render_template("category_list.html", count=len(medicine_list), medicine_list=medicine_list)
    data["dom"].append({"selector": "#content", "html": html})
    return data


def cmd_article(data: dict) -> dict:

    article = []
    headers = internal.read_db("article_read.sql", {"id": data["params"]["value"]})
    for h in headers:
        article.append({"id": h["id"], "text": h["txt"], "paragraph": []})
        # article.update({h["id"]: {"header": h["txt"], "text": {}}})
        paragraphs = internal.read_db("article_read.sql", {"id": h["id"]})
        for p in paragraphs:
            article[-1]["paragraph"].append({"id": p["id"], "text": p["txt"]})
        pass
    data["dom"].append({"selector": "#content", "html": render_template("article.html", article=article)})
    return data


def cmd_search(data: dict) -> dict:
    sr = do_search(data['params']['value'])
    html =  render_template("search.html",search_info = sr['search_info'], search_result = sr['search_result'],)
    # return {'search_info':search_info,'search_result':search_result}
    data["dom"].append({"selector": "#content", "html":html})
    return data
    
"""    
    needle = data["params"]["value"].strip().upper()
    html = ""
    if len(needle):
        cur = db_conn().execute("select * from articles")
        try:
            while True:
                data = cur.fetchone()
                if data is None:
                    break
                hash = data['txt'].upper()
                if needle in hash
                pass
                # if 
        finally:
            cur.close()

    return data
"""

"""
    # 
    html = f"search: {data['params']['value']}<br><br>"
    current_dir = os.path.dirname(os.path.realpath(__file__))
    index_dir = os.path.join(current_dir, "index")
    ix = open_dir(index_dir)
    with ix.searcher() as searcher:
        query = QueryParser("content", ix.schema).parse(data["params"]["value"])
        results = searcher.search(query, terms=True)
        for hit in results:

            html = f"{html}{hit['title']}<br>"
            # print(hit["title"])
            # Assume "content" field is stored
            html = f"{html}{hit.highlights('content')}<br>"
            # print(hit.highlights("content"))

    
            for r in results:
            print(r, r.score)
            print("-" * 40)
            # Was this results object created with terms=True?
            if results.has_matched_terms():
                # What terms matched in the results?
                print(results.matched_terms())
                print("-" * 40)

    print(len(html))
    data["dom"].append({"selector": "#content", "html": html})
    return data
    tmp_article = internal.read_db("get_article.sql", {"medicine_id": data["params"]["value"]})
    article = []
    for p in tmp_article:
        if p["is_header"]:
            article.append({"header": p["article_text"], "text": []})
        else:
            if len(article) == 0:
                continue
            article[-1]["text"].append(p["article_text"])
    data["dom"].append({"selector": "#content", "html": render_template("article.html", article=article, medicine_id=data["params"]["value"])})
    
    """


@app.route("/")
def main():
    categories = internal.read_db("categories_list.sql")
    return render_template("main.html", categories=categories)


@app.route("/parse_data", methods=["POST"])
def parse_data():

    data = json.loads(request.get_data())
    result = {"dom": [], "data": {}, "params": {"command": data["command"], "value": data["value"]}}

    if data["command"] == COMMAND_LIST:
        result = cmd_list(result)

    elif data["command"] == COMMAND_SEARCH:
        result = cmd_search(result)

    elif data["command"] == COMMAND_ARTICLE:
        result = cmd_article(result)

    return jsonify(result)


# {'dom': [], 'data': {}, 'params': {'command': 2, 'value': 106}}
