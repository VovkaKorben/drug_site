
select c.category_id,c.category_name,cval.ccnt from

(SELECT mc.category_id AS cid, COUNT(mc.category_id) AS ccnt FROM medicine_categories mc GROUP BY mc.category_id
UNION 
SELECT 0 , COUNT(mc.category_id) FROM medicine_categories mc) as cval

LEFT JOIN categories c ON c.category_id = cval.cid
order by c.order_no;