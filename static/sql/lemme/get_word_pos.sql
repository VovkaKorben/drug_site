 SELECT word_index,start,len 
 from lemmas_usage 
 where 
 article_id=:article_id
 AND 
 word_index in (:windexes) 
 order by word_index;
        