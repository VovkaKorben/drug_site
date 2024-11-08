import math, re, sqlite3, itertools
from Levenshtein import ratio
from internal import flask_db_conn
import pymorphy3
from internal import read_db
import copy

MAX_RESULTS = None  # или число для ограничения
HTML_TAGS = ('<span class="search">', "</span>")
# сколько слов влево/вправо показывается в результатах поиска
WORDS_FRAMING = 12

OPEN_TAG = 0
CLOSE_TAG = 1
morph = pymorphy3.MorphAnalyzer()

blacklist_words = [
    "БЕЗ",
    "ВО",
    "ГДЕ",
    "ДЛЯ",
    "ДО",
    "ЕСТЬ",
    "ЖЕ",
    "ИЗ",
    "ИЛИ",
    "КАК",
    "НА",
    "НАД",
    "НЕ",
    "НО",
    "ОБА",
    "ОТ",
    "ПО",
    "ПОД",
    "ПРИ",
    "ТАК",
    "ТАКЖЕ",
    "ТО",
    "УЖЕ",
    "ХОТЯ",
    "ЧЕМ",
    "ЧТО",
    "ЭТО",
    "ЛИ",
    "ОН",
    "ОНО",
    "ОНА",
    "ОНИ",
    "ЕГО",
    "ЕЁ",
    "ИХ",
    "ВСЕ",
    "ВСЁ",
    "САМ",
    "ЧЕЙ",
]


def sqlite_trace_callback(value):
    # return
    # url = flask.request.base_url
    # url = url.split("/")[-1:]
    # url = url[0]

    value = value.replace("\n", " ")
    while value.find("  ") != -1:
        value = value.replace("  ", " ")

    sqlite3log = open("sqlite3.log", "a")
    # sqlite3log.write(f"[{url}] {value}\n")
    sqlite3log.write(f"{value}\n")
    sqlite3log.close()


def tokenize_string(line: str) -> dict:

    def add_word(start: int, end: int, word_index: int):

        word = line[start:end]
        if word not in blacklist_words:
            morphem = morph.parse(word)[0].normal_form.upper()
            if morphem not in blacklist_words and len(morphem) > 1 and len(word) > 1:
                r.append(
                    {
                        "word": line[start:pos],
                        "morphem": morphem,
                        "start": start,
                        "len": end - start,
                        "word_index": word_index,
                    }
                )
                word_index += 1
        return word_index

    allowed_chars = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЬЫЪЭЮЯ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-_"
    line = line.upper()
    text_len = len(line)
    pos, word_index = 0, 0
    start = None

    r = []
    while pos < text_len:
        if line[pos] in allowed_chars:
            if start is None:
                start = pos
        else:
            if start is not None:
                word_index = add_word(start, pos, word_index)
                start = None

        pos += 1
    # check if line ends with word
    if start is not None:
        add_word(start, text_len, word_index)
    return r


def make_dicts(cursor, row):

    return dict((cursor.description[idx][0], value) for idx, value in enumerate(row))


def get_articles_parent(articles_id: list, conn) -> dict:
    cache = {}
    # проверяем всё в кеше
    retrieve = articles_id
    while True:

        retrieve_keys = [item for item in retrieve if item not in cache]
        if len(retrieve_keys) == 0:
            break
        params = ",".join(["?"] * len(retrieve_keys))
        cur = conn.execute(f"SELECT * FROM articles where id in ({params});", retrieve_keys)
        articles = cur.fetchall()
        retrieve = []

        for a in articles:
            cache[a["id"]] = {
                "parent": a["parent"],
                "word_count": a["word_count"],
            }
            if a["parent"] is not None:
                retrieve.append(a["parent"])
    return cache


def get_articles_text(articles_id: list, conn) -> dict:
    articles = {}
    params = ",".join(["?"] * len(articles_id))
    cur = conn.execute(
        f"SELECT id,txt,word_count FROM articles where id in ({params});",
        articles_id,
    )
    while True:
        a = cur.fetchone()
        if a is None:
            break
        articles[a["id"]] = {"txt": a["txt"], "word_count": a["word_count"]}
    # articles = cur.fetchall()
    return articles


def levenshtein_ratio(str1, str2):
    return ratio(str1, str2)


def insert_markup(text: str, insert_positions, tag_markup):
    # sort inserting positions by increasing
    insert_positions = sorted(insert_positions, key=lambda x: x[0])

    add_value = 0
    for ins_data in insert_positions:
        ins_pos = ins_data[0] + add_value
        if len(text) < ins_pos:
            break
        text = text[:ins_pos] + tag_markup[OPEN_TAG] + text[ins_pos:]
        ins_pos += len(tag_markup[OPEN_TAG]) + ins_data[1]
        ins_pos = min(ins_pos, len(text))
        text = text[:ins_pos] + tag_markup[CLOSE_TAG] + text[ins_pos:]
        add_value += len(tag_markup[OPEN_TAG]) + len(tag_markup[CLOSE_TAG])

    return text


def shortenize(id, params, texts, conn):
    # def get_by_key(data, key_name, value):        return next((item for item in data if item[key_name] == value), None)

    params = params[id]
    texts = texts[id]

    anchor_word = params["comb"][0]
    # берем первое слово, будем отталкиваться от него
    if len(params["comb"]) > 1:
        word_index = params["tokens"][anchor_word[0]][anchor_word[1]]["word_index"]
    else:
        word_index = params["tokens"][0][0]["word_index"]
    #  params["tokens"][0][params["comb"][0]]["word_index"]

    start_word_index = word_index - WORDS_FRAMING
    end_word_index = word_index + WORDS_FRAMING
    if start_word_index < 0:
        start_word_index = 0
        end_word_index = min(texts["word_count"] - 1, WORDS_FRAMING * 2)
    if end_word_index >= texts["word_count"]:
        end_word_index = texts["word_count"] - 1
        start_word_index = max(0, end_word_index - WORDS_FRAMING * 2)

    # читаем из базы позиции начальных и конечных слов, по ним режем строку
    db_word_positions = read_db(
        sql_filename="lemme/get_word_pos.sql",
        params={
            "article_id": id,
            "windexes": [start_word_index, end_word_index],  # добавляем начало и конец, по ним будем резать фразу
        },
    )

    # срезаем нашу строку
    char_start = db_word_positions[0]["start"]  # lemmas_usage[start_word_index][0]
    char_end = db_word_positions[1]["start"] + db_word_positions[0]["len"]  # lemmas_usage[end_word_index][0] + lemmas_usage[end_word_index][1]
    result = texts["txt"][char_start : char_end + 1]

    # все токены из всех комбинаций проверяем на вхождение в диапазон, входящие добавляем в массив и сортируем по word index
    # потом этот отсортированный массив передаем как markup
    markup = []
    for token_set in params["tokens"]:
        for token in token_set:
            if start_word_index <= token["word_index"] and end_word_index >= token["word_index"]:
                markup.append((token["start"] - char_start, token["len"]))
            # print(token)
    """
    # находим все слова из поиска, которые входят в наш показываемый диапазон
    # включая (?) то самое первое слово, взятое за основу
    used_words = []
    if len(params["comb"]) > 1:

        for token_index in range(len(params["comb"])):
            t = params["comb"][token_index]
            word_index = params["tokens"][t[0]][t[1]]["word_index"]
            # tmp = params["tokens"][no][params["comb"][no]]["word_index"]
            if word_index >= start_word_index and word_index <= end_word_index:
                used_words.append(word_index)
    else:
        used_words.append(word_index)

    # читаем из базы позиции слов
    db_word_positions = read_db(
        sql_filename="lemme/get_word_pos.sql",
        params={
            "article_id": id,
            "windexes": used_words + [start_word_index, end_word_index],  # добавляем начало и конец, по ним будем резать фразу
        },
    )
    # переделываем в удобоваримый вид
    lemmas_usage = {}
    for x in db_word_positions:
        lemmas_usage[x["word_index"]] = [x["start"], x["len"]]

    # срезаем нашу строку
    char_start = lemmas_usage[start_word_index][0]
    char_end = lemmas_usage[end_word_index][0] + lemmas_usage[end_word_index][1]
    result = texts["txt"][char_start : char_end + 1]

    # готовим массив со словами и вставляем ссылки
    markup = []

    for db_word_positions in list(used_words):
        x = lemmas_usage[db_word_positions]
        x[0] -= char_start
        markup.append(x)

        # markup[tmp] = sql_result[tmp]
        # markup[tmp][0] -= char_start
    """
    result = insert_markup(result, markup, HTML_TAGS)

    # добавляем трёхточие, если была обрезка
    if start_word_index != 0:
        result = "..." + result
    if end_word_index != (texts["word_count"] - 1):
        result = result + "..."
    return result


def do_search(needle: str, conn=None):

    def generate_combinations(result, arrays, array_index=0, current_combination=[]):
        #  Если достигли конца списка массивов
        if array_index == len(arrays):
            #  Добавить текущую комбинацию в список комбинаций
            result.append(current_combination.copy())
            return result

        #  Если текущий массив пуст, пропускаем его и переходим к следующему
        if len(arrays[array_index]) == 0:
            generate_combinations(result, arrays, array_index + 1, current_combination)
        else:
            #  Итерируемся по каждому элементу текущего массива
            for element_index in range(len(arrays[array_index])):
                #  Добавляем элемент к текущей комбинации
                current_combination.append((array_index, element_index))

                #  Рекурсивно вызываем функцию для следующего массива
                result = generate_combinations(result, arrays, array_index + 1, current_combination)

                #  Удаляем последний элемент для возврата к предыдущему состоянию
                current_combination.pop()
        return result

    if conn is None:
        conn = flask_db_conn()
    needle = tokenize_string(needle)
    needle_len = len(needle)
    s_res = {}

    # готовим временную таблицу, куда заносим наш поисковый запрос...
    conn.create_function("levenshtein_ratio", 2, levenshtein_ratio)
    conn.execute("DROP TABLE if EXISTS 'needle';")
    conn.execute("CREATE TABLE 'needle'('dict_index' INT,'order_no' INT, 'morphem' TEXT,'ratio' real);")

    # ... и наполняем её, индекс токена и коэффициент сравнения со словарём
    tmp = 0

    for token in needle:
        read_db(
            # sql_query=f"insert into 'needle' ('morphem','order_no') values ('{token['morphem']}',{tmp});",
            sql_query=f"insert into 'needle' ('morphem','order_no') values (:morphem,:order_no);",
            result_required=False,
            params={
                "morphem": token["morphem"],
                "order_no": tmp,
            },
        )
        # conn.execute(sql)
        read_db(
            sql_query=f"update 'needle' set ('dict_index','ratio')=(select 'lemmas'.'id', levenshtein_ratio('needle'.'morphem','lemmas'.'lemma') lr from 'lemmas' order by lr desc limit 1) WHERE 'needle'.'order_no'=:order_no;",
            result_required=False,
            params={
                "order_no": tmp,
            },
        )
        # conn.execute(sql)
        conn.commit()
        # del sql
        tmp += 1
    del tmp

    # обновляем леммы из словаря (чтобы были не морфемы) (напр. дельфины -> ДЕЛЬФИН)
    query_result = read_db(sql_query=f"select n.order_no,n.dict_index,l.lemma from needle n,lemmas l where n.dict_index = l.id;")
    for qr in query_result:

        needle[qr["order_no"]].update({"dict_index": qr["dict_index"], "lemma": qr["lemma"]})
    del qr, query_result

    # находим токены в статьях, заполняем нахождение в статьях наших токенов
    query_result = read_db(sql_query="SELECT needle.order_no,lemmas_usage.* FROM needle,lemmas_usage WHERE needle.dict_index=lemmas_usage.lemma_id;")
    for qr in query_result:
        if not qr["article_id"] in s_res:

            s_res[qr["article_id"]] = {"tokens": [[] for _ in range(len(needle))]}
        s_res[qr["article_id"]]["tokens"][qr["order_no"]].append(
            {
                "start": qr["start"],
                "len": qr["len"],
                "word_index": qr["word_index"],
            }
        )

    # читаем данные о статьях (нам нужны заголовки), также сразу берем данные о количестве токенов в статье, для сравнения
    articles_parent = get_articles_parent(list(s_res), conn)

    # в зависимости от количества токенов в запросе делаем вычисления

    if needle_len > 1:
        # находим максимальное возможное количество результатов, чтобы отбросить ситуации, когда слова два, а в статье нашлось одно
        max_len = None

        for article_id in s_res:
            current_len = needle_len - s_res[article_id]["tokens"].count([])
            if max_len is None or (max_len is not None and max_len < current_len):
                max_len = current_len

        # отбрасываем результаты, где найденных токенов меньше, чем max_len

        for article_id in list(s_res):
            current_len = needle_len - s_res[article_id]["tokens"].count([])
            if current_len < max_len:
                del s_res[article_id]
        # del max_len, current_len

        # для оставшихся результатов считаем лучшее расстояние между словами
        max_deviation = 0

        for article_id in list(s_res):
            best_value, best_comb = None, None
            token_shortcut = s_res[article_id]["tokens"]

            #  Пример использования
            index_combinations = generate_combinations([], token_shortcut)

            for combination in index_combinations:
                number_set = []
                for i in combination:
                    number_set.append(token_shortcut[i[0]][i[1]]["word_index"])

                standard_dev = math.sqrt(sum([(x - sum(number_set) / needle_len) ** 2 for x in number_set]) / needle_len)
                if best_comb is None or (best_comb is not None and best_value > standard_dev):
                    best_comb = combination
                    best_value = standard_dev
                # del number_set, standard_dev
            # del comb
            # search_result[article_id]['dev'] = {'comb':best_comb,'value':1-(best_value/articles_cache[article_id]['word_count'])}
            s_res[article_id]["comb"] = best_comb
            s_res[article_id]["value"] = best_value
            max_deviation = max(max_deviation, best_value)
            # search_result[article_id]['t1'] =best_value/articles_cache[article_id]['word_count']
        # del best_value, best_comb

        # нормализируем СКО к 0...1

        for article_id in list(s_res):
            s_res[article_id]["value"] = 1 - s_res[article_id]["value"] / max_deviation
        # del max_deviation
    else:  # если слово в поиске одно - то берем первую комбинацию и СКО = 0

        for article_id in list(s_res):
            # search_result[article_id]['dev'] = {'comb':(0),'value':0}
            s_res[article_id]["comb"] = (0,)
            s_res[article_id]["value"] = 0
        del article_id

    # вторая оценка, отношение количества слов в поиске к количеству слов в статье

    for article_id in list(s_res):
        s_res[article_id]["word_ratio"] = needle_len / articles_parent[article_id]["word_count"]
    del article_id
    # сортируем результаты по сумме двух оценок
    s_res = dict(
        sorted(
            s_res.items(),
            key=lambda item: -item[1]["value"] - item[1]["word_ratio"],
        )
    )

    # отбрасываем если результатов много
    total_results = len(s_res)
    if MAX_RESULTS is not None:
        showed = min(total_results, MAX_RESULTS)
        s_res = dict(list(s_res.items())[:showed])
    else:
        showed = total_results

    # строим дерево результатов, сразу накапливаем ID статей, для запроса текстов
    search_tree = {}
    collect_id = []

    for article_id in list(s_res)[:showed]:

        article_line, id = [], article_id
        # находим обратную цепочку, от детей к паренту
        while id is not None:
            # собираем айдишки
            if not (id in collect_id):
                collect_id.append(id)
            article_line.insert(0, id)
            id = articles_parent[id]["parent"]

        # вытаскиваем родительский ID и строим дерево от него
        id = article_line.pop(0)
        if not (id in search_tree):
            search_tree[id] = []
        search_tree[id].append(article_line)
        del id, article_line
    del article_id

    # get_articles_text

    query_result = read_db(
        sql_filename="article_work/get_articles_text.sql",
        params={"id": collect_id},
    )
    articles_text = {}
    for qr in query_result:
        articles_text[qr["id"]] = {"txt": qr["txt"], "word_count": qr["word_count"]}

    # выводим общие параметры, использованные в поиске
    search_info = [f"Результатов поиска: {total_results}"]
    if total_results != showed:
        search_info[0] = f"{search_info[0]} (показано: {showed})"

    lemmas_used = ", ".join([n["lemma"].lower() for n in needle])
    search_info.append(f"Использованы: {lemmas_used}")

    search_result = []

    for article_id in search_tree:
        # заголовок статьи
        article = {
            # "txt": articles_text[article_id],
            "txt": articles_text[article_id]["txt"],
            "id": article_id,
            "lines": [],
        }

        for branch in search_tree[article_id]:
            line = []
            if len(branch) > 0:  # for header
                line.append(
                    {
                        "txt": articles_text[branch[0]]["txt"],
                        # "txt": articles_text[branch[0]],
                        "id": branch[0],
                    }
                )
            if len(branch) > 1:  # for paragraph

                # укороченное содержание
                shortened = shortenize(branch[1], s_res, articles_text, conn)
                line.append(
                    {
                        "txt": shortened,
                        "id": branch[1],
                    }
                )
            else:  # for article
                # проверяем, есть ли ещё строки для данной статьи
                # если нет - то выводим "название препарата"
                if len(search_tree[article_id]) == 0:
                    line.append(
                        {
                            "txt": "no paragraph",
                            "id": 0,
                        }
                    )
                """
                # для всех, кроме последнего, выводим полностью
                for id in branch[:-1]:
                    line.append({"txt": articles_text[id]["txt"], "id": id})

                # последнее, с леммами
                id = branch[-1]
                shortened = shortenize(id, s_res, articles_text, conn)
                line.append(
                    {
                        "txt": shortened,
                        "id": id,
                    }
                )"""
            if len(line) > 0:
                article["lines"].append(line)
        search_result.append(article)

    return {
        "search_info": search_info,
        "search_result": search_result,
        "needle": needle,
    }


"""
def main():
    conn = sqlite3.connect("C:\\drug_site\\drugs.db")
    conn.row_factory = make_dicts
    conn.set_trace_callback(sqlite_trace_callback)
    # r = do_search( "симптомы депрессии", conn)
    r = do_search("антидепресс", conn)
    print(r)


if __name__ == "__main__":
    main()
"""
