import oracledb
import pandas as pd
import api_keys

query = """
select DISTINCT
pi.item_ark as ark,
dt.term_label as term,
v_qual.qual_text as type,
CASE WHEN dv.desc_cvid_fk IS NOT NULL THEN ctrl_values.ctrl_val_text 
    ELSE dv.desc_value
  END as value,
ctrl_values.source as source
FROM
project_items pi,
desc_values dv,
desc_terms dt,
core_desc_terms cdt,
(select distinct dq.core_desc_qualifierid_fk as qid,cdq.desc_qualifier as qual_text,dq.desc_qualifierid_pk as desc_qual_pk
from
desc_qualifiers dq,
core_desc_qualifiers cdq
where dq.core_desc_qualifierid_fk = cdq.core_desc_qualifierid_pk) v_qual,
(select distinct cdcv.core_desc_cv as ctrl_val_text, dcv.desc_cvid_pk,cdcv.core_desc_cvid_pk, cdcv.core_desc_cv_source as source
from
core_desc_control_values cdcv,
desc_control_values dcv
where cdcv.core_desc_cvid_pk = dcv.core_desc_cvid_fk) ctrl_values 
WHERE
dv.projectid_fk = 80 AND
dv.divid_fk = pi.divid_pk AND
dv.desc_termid_fk=dt.desc_termid_pk AND
dt.core_desc_termid_fk=cdt.core_desc_termid_pk AND
dv.desc_qualifierid_fk=v_qual.desc_qual_pk(+) AND
dv.desc_cvid_fk = ctrl_values.desc_cvid_pk(+)  
"""

con = oracledb.connect(
    user=api_keys.USER,
    password=api_keys.PASSWORD,
    dsn=api_keys.DSN)

df_ora = pd.read_sql_query(query, con)

con.close()

df_ora = df_ora.replace({r'\r\n': ''}, regex=True)

for i, g in df_ora.groupby('TERM'):
	g.drop('TERM', axis=1).to_csv('{}.tsv'.format(i.replace(" ", "_").split('/')[0]), index=False, sep='\t')
