# File:     recent_docs_updated.sql
# Desc:     Find papers with metadata/author updates during the previous hour.
# Based on: arxiv-bin/notify_search.pl
# Running:  see arxiv-bin/dotfiles/nexus.crontab
#

SELECT am.paper_id
  FROM arXiv_paper_owners apo,
       arXiv_metadata     am
 WHERE apo.document_id = am.document_id
   AND apo.valid       = 1 
   AND apo.flag_author = 1 
   AND apo.flag_auto   = 0
   AND apo.date BETWEEN UNIX_TIMESTAMP(DATE_SUB(DATE_FORMAT(NOW(), "%Y-%m-%d %H:00:00"), INTERVAL 1 HOUR))
                    AND UNIX_TIMESTAMP(DATE_FORMAT(NOW(), "%Y-%m-%d %H:00:00"))
UNION
SELECT am.paper_id
  FROM arXiv_paper_owners apo,
       arXiv_metadata     am,
       arXiv_author_ids   aai
 WHERE apo.document_id = am.document_id
   AND apo.user_id     = aai.user_id
   AND apo.valid       = 1 
   AND apo.flag_author = 1 
   AND apo.flag_auto   = 0
   AND aai.updated BETWEEN DATE_SUB(DATE_FORMAT(NOW(), "%Y-%m-%d %H:00:00"), INTERVAL 1 HOUR)
                       AND DATE_FORMAT(NOW(), "%Y-%m-%d %H:00:00")
UNION
SELECT am.paper_id
  FROM arXiv_paper_owners apo,
       arXiv_metadata     am,
       arXiv_orcid_ids    aoi
 WHERE apo.document_id = am.document_id
   AND apo.user_id     = aoi.user_id
   AND apo.valid       = 1 
   AND apo.flag_author = 1 
   AND apo.flag_auto   = 0
   AND aoi.updated BETWEEN DATE_SUB(DATE_FORMAT(NOW(), "%Y-%m-%d %H:00:00"), INTERVAL 1 HOUR)
                       AND DATE_FORMAT(NOW(), "%Y-%m-%d %H:00:00")
UNION
SELECT am.paper_id
  FROM arXiv_metadata am
 WHERE 1=1
   AND am.modtime BETWEEN UNIX_TIMESTAMP(DATE_SUB(DATE_FORMAT(NOW(), "%Y-%m-%d %H:00:00"), INTERVAL 1 HOUR))
                      AND UNIX_TIMESTAMP(DATE_FORMAT(NOW(), "%Y-%m-%d %H:00:00"))
ORDER BY 1 desc
;

