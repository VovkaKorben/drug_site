SELECT DISTINCT
	medicines.*
FROM
	medicines,
	medicine_categories
WHERE
	medicines.medicine_id = medicine_categories.medicine_id
	AND ( medicine_categories.category_id = :category_id OR :category_id=0 ) 
ORDER BY
	medicines.medicine_name