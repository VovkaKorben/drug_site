SELECT id,txt,word_count
FROM articles where id in (:id);
