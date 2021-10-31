import os
from datetime import (
    datetime as dt,
    timedelta
)
from kavalkilu import (
    LogWithInflux,
    DateTools,
    InfluxDBLocal,
    InfluxDBPiHole,
    SQLLiteLocal,
    Hosts
)
from servertools import SlackComm


logg = LogWithInflux('pihole_etl', log_to_db=True)
sc = SlackComm(parent_log=logg)
hosts = {x['ip']: x['name'] for x in Hosts().get_all_hosts()}
datetools = DateTools()

FTL_DB_PATH = os.path.join('/etc', *['pihole', 'pihole-FTL.db'])
sqll = SQLLiteLocal(FTL_DB_PATH)

INTERVAL_MINS = 60
end = dt.now().astimezone().replace(second=0, microsecond=0)
start = (end - timedelta(minutes=INTERVAL_MINS))
unix_start = datetools.dt_to_unix(start, from_tz='US/Central')
unix_end = datetools.dt_to_unix(end, from_tz='US/Central')

query = f"""
    SELECT
        client
        , domain
        , CASE
            WHEN status = 0 THEN 'UNKNOWN'
            WHEN status = 1 OR status > 3 THEN 'BLOCKED'
            WHEN status = 2 OR status = 3 THEN 'ALLOWED' 
            ELSE 'UNKNOWN'
        END AS query_status
        , CASE
            WHEN status = 0 THEN 'NO ANSWER'
            WHEN status = 1 THEN 'IN GRAVITY'
            WHEN status = 2 THEN 'FORWARDED'
            WHEN status = 3 THEN 'FROM CACHE'
            WHEN status = 4 THEN 'REGEX MATCH'
            WHEN status = 5 THEN 'EXACT MATCH'
            WHEN status = 6 THEN 'UPSTREAM KNOWN IP'
            WHEN status = 7 THEN 'UPSTREAM ALL IP'
            WHEN status = 8 THEN 'UPSTREAM NXDOMAIN'
            WHEN status = 9 THEN 'IN GRAVITY CNAME'
            WHEN status = 10 THEN 'REGEX MATCH CNAME'
            WHEN status = 11 THEN 'EXACT MATCH CNAME' 
            ELSE 'UNKNOWN'
        END AS status_info
        , timestamp
        , COUNT(DOMAIN) AS query_cnt
    FROM
        queries
    WHERE
        domain != ''
        AND timestamp BETWEEN '{unix_start}' AND '{unix_end}'
    GROUP BY
        timestamp
        , client
        , domain
        , query_status
        , status_info
"""

df = sqll.read_sql(query)
logg.debug(f'Returned {df.shape[0]} rows of data.')
# Convert unix back to dt
df['timestamp'] = df['timestamp'].apply(lambda x: datetools.unix_to_dt(x, to_tz='US/Central'))
# Lookup all known clients
df['client'] = df['client'].replace(hosts)

# Feed data into influx
influx = InfluxDBLocal(InfluxDBPiHole.QUERIES)
logg.debug('Writing dataframe to influx table.')
influx.write_df_to_table(df, tags=['client', 'domain', 'query_status', 'status_info'],
                         value_cols=['query_cnt'], time_col='timestamp')

logg.close()
