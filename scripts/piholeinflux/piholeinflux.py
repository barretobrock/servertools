import os
from datetime import datetime as dt, timedelta
from kavalkilu import Log, DateTools, InfluxDBLocal, InfluxDBNames, InfluxTblNames
from servertools import SlackComm, SQLLiteLocal


logg = Log('pihole_etl', log_to_db=True)
sc = SlackComm()
datetools = DateTools()

FTL_DB_PATH = os.path.join(os.path.expanduser('~'), *['Downloads', 'pihole-FTL.db'])
sqll = SQLLiteLocal(FTL_DB_PATH)

INTERVAL_MINS = 60
end = dt.now()
start = (end - timedelta(minutes=INTERVAL_MINS)).replace(second=0, microsecond=0)

query = """
    SELECT
        client
        , domain
        , status
        , CASE
            WHEN status = 0 THEN 'unknown'
            WHEN status = 1 OR status > 3 THEN 'blocked'
            WHEN status = 2 THEN 'forwarded'
            WHEN status = 3 THEN 'known from cache' 
            ELSE 'unknown'
        END AS status_type
        , timestamp
        , COUNT(DOMAIN)
    FROM
        queries
    WHERE
        domain != ''
        --AND timestamp BETWEEN '{}' AND '{}'
    GROUP BY
        timestamp
        , client
        , domain
        , status_type
        , status
    LIMIT 10
""".format(datetools.dt_to_unix(start), datetools.dt_to_unix(end))

df = sqll.read_sql(query)
