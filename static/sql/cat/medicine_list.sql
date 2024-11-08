SELECT
	DISTINCT a.id,
	a.txt 
FROM
	medicine_categories mc,
	articles a 
WHERE
	mc.medicine_id = a.id 
	AND ( mc.category_id = :category_id OR :category_id = 0 ) 
ORDER BY
	a.txt;