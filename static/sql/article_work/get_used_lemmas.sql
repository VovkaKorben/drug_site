SELECT
    lu.article_id,
    lu.start,
    lu.len
FROM
    lemmas_usage lu
WHERE
    lu.article_id IN (:articles_list)
    AND lu.lemma_id IN (:lemmas_list)
ORDER BY lu.'article_id',lu.'start';