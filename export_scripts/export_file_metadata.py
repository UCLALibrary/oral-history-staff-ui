import warnings

# oracledb and pandas are installed locally, not within the project.
import oracledb
import pandas as pd

# Not included in repo, ask a colleague.
import api_keys


# Because pandas complains about old-school connections,
# and I don't want to install sqlalchemy as well.........
warnings.filterwarnings("ignore", category=UserWarning)


def _get_query() -> str:
    query = """
        select
        -- These fields are needed for migration
            fg.file_group_title
        ,	cf.content_type
        ,	p.item_ark
        ,	cf.file_use
        ,	cf.file_sequence as seq
        ,	cf.file_size
        ,	to_char(cf.create_date, 'YYYY-MM-DD HH24:MI:SS') as create_date
        ,	cf.file_location
        ,	cf.file_name
        from file_groups fg
        inner join content_files cf on fg.file_groupid_pk = cf.file_groupid_fk
        inner join project_items p on cf.divid_fk = p.divid_pk
        where fg.projectid_fk = 80 -- Oral History
        and cf.create_date <= sysdate
        order by p.item_ark, cf.file_sequence, cf.create_date desc
    """
    return query


def main() -> None:
    conn = oracledb.connect(
        user=api_keys.USER, password=api_keys.PASSWORD, dsn=api_keys.DSN
    )
    query = _get_query()
    df_ora = pd.read_sql_query(query, conn)
    conn.close()
    df_ora.to_csv("file_metadata.tsv", index=False, sep="\t")


if __name__ == "__main__":
    main()
