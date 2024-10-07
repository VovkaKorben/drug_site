import pymorphy2
import re
from Levenshtein import ratio
import sqlite3
import itertools

morph = pymorphy2.MorphAnalyzer()
LEVENSTAIN_TRESHOLD = 0.1
needle = "иследования печенни"
def tokenize_string(text:str)->dict:
    def add_word(w:str):
        bw = ['А','В','ТАК','КАК','ГДЕ','И','О','НЕ','ПРИ','С','ТАКЖЕ','ЖЕ','ПО','ЧТО','ПОД','НАД','БЕЗ','ВО','НА','ИЛИ']
        if w not in bw:
            lemma = morph.parse(w)[0].normal_form.upper()
            r.append({'word':text[start:pos],'lemma':lemma,'start':start,'end':pos})
            

    ab = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЬЫЮЭЮЯ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    
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


def make_dicts(cursor, row):
    return dict((cursor.description[idx][0], value) for idx, value in enumerate(row))


def search_str(hash_id:int,hash:str):
    def filled_count(a:list)->int:
        r = 0
        for v in a:
            if len(v)>0:
                r+=1
        return r
    def find_tokens(hash:str):
        hash_expl = tokenize_string(hash)
        token_finded = [[] for _ in range(len(needle))]

        for needle_word_index in range(len(needle)):
            nw = needle[needle_word_index]
            for hash_word_index in range(len(hash_expl)):
                hw = hash_expl[hash_word_index]
                r = ratio(hw['lemma'],nw['lemma'])
                if r>=LEVENSTAIN_TRESHOLD:
                    token_finded[needle_word_index].append((hash_word_index,r))
        return token_finded

    ft = find_tokens(hash)
    # считаем количество найденных слов
    token_finded_count = filled_count(ft)
    if token_finded_count>0:
        phrases[token_finded_count-1].append({'id':hash_id,'data':ft})
    
"""
# Пример списка с неизвестным количеством вложенных списков
nested_lists = [[1, 2], ['a', 'b', 'c'], [True, False]]
# Используем itertools.product для генерации всех комбинаций индексов
combinations_of_indices = list(itertools.product(*[range(len(sublist)) for sublist in nested_lists]))

# Вывод всех комбинаций индексов
for indices in combinations_of_indices:
    print(indices)

    


# Используем itertools.product для генерации всех комбинаций
combinations = list(itertools.product(*nested_lists))

# Вывод всех комбинаций
for combination in combinations:
    print(combination)
"""



needle = tokenize_string(needle)
phrases = [[] for _ in range(len(needle))]

try:
    conn = sqlite3.connect("C:\\drug_site\\drugs.db")
    conn.row_factory = make_dicts
    cur = conn.execute("select * from articles")
    while True:
        a = cur.fetchone()
        if a is None:
            break
        # ss = 
        search_str(a['id'],a['txt'])
    pass
            
finally:
    cur.close()
    conn.close()

