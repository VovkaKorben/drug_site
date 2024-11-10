SELECT
	c.category_id,
	c.category_name,
	cval.ccnt 
FROM
	(
			SELECT mc.category_id AS cid,COUNT(mc.category_id) AS ccnt FROM medicine_categories mc GROUP BY mc.category_id
		UNION
			SELECT 0,COUNT(DISTINCT mc.medicine_id) FROM medicine_categories mc
	)
AS cval

LEFT JOIN categories c ON c.category_id = cval.cid 
ORDER BY c.order_no;