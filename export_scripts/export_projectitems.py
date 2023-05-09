import oracledb
import pandas as pd

# Not included in repo, ask a colleague.
import api_keys

query = """
select 
    a.item_ark as ark,
    c.coverage,
    a.create_date,
    coalesce(uc.email, 'oralhistory@library.ucla.edu') as created_by,
    a.last_edit_date as last_modified_date,
    coalesce(um.email, 'oralhistory@library.ucla.edu') as last_modified_by,
    b.item_ark as parent_ark,
    r.relation as relation,
    a.item_sequence as sequence,
    qa.status,
    a.node_title as title,
    o.object_label as type
from project_items a
    left outer join project_items b on a.parent_divid = b.divid_pk
    left outer join qa_status qa on a.statusid_fk = qa.statusid_pk
    left outer join dl_objects o on a.objectid_fk = o.objectid_pk
    left outer join users uc on a.created_by = uc.user_name
    left outer join users um on a.modified_by = um.user_name
    left outer join (select listagg(desc_value, ',') as relation, divid_fk from desc_values
where 
    projectid_fk = 80 and
    desc_termid_fk = 899
group by divid_fk) r on a.divid_pk = r.divid_fk
left outer join (select listagg(desc_value, ',') as coverage, divid_fk from desc_values
where 
    projectid_fk = 80 and
    desc_termid_fk = 900
group by divid_fk) c on a.divid_pk = c.divid_fk
where a.projectid_fk = 80 order by create_date
"""

con = oracledb.connect(user=api_keys.USER, password=api_keys.PASSWORD, dsn=api_keys.DSN)

df_ora = pd.read_sql_query(query, con)

con.close()

df_ora = df_ora.replace({r"\r\n": ""}, regex=True)
df_ora.to_csv("project-items-export.tsv", index=False, sep="\t")
