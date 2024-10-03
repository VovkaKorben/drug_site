SELECT
	a.article_text,
	a.is_header 
FROM
	articles a 
WHERE
	medicine_id = :medicine_id 
ORDER BY
	order_no