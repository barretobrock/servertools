from datetime import datetime
from pathlib import Path
import re
import tempfile
from typing import (
    List,
    Tuple,
)

from kavalkilu import (
    InfluxDBHomeAuto,
    InfluxDBLocal,
    Keys,
)
from pukr import get_logger
from smb.SMBConnection import SMBConnection

from servertools import (
    LOG_DIR,
    SlackComm,
)

log = get_logger('timelapse', log_dir_path=LOG_DIR.joinpath('timelapse'))
influx = InfluxDBLocal(dbtable=InfluxDBHomeAuto.LOGS, app_name='timelapse_poster')


@influx.influx_exception_decorator(logger=log)
def connect_to_smb() -> Tuple[SMBConnection, str]:
    creds = Keys().get_key('timelapse_poster')
    log.info('Connecting to smb...')
    conn = SMBConnection(
        username=creds['un'],
        password=creds['pw'],
        my_name=creds['my_name'],
        remote_name=creds['remote_name'],
        use_ntlm_v2=True
    )
    conn.connect(ip=creds['smp_ip'])

    svc_name = creds['service_name']
    return conn, svc_name


@influx.influx_exception_decorator(logger=log)
def get_files(conn: SMBConnection, svc_name: str) -> List[str]:
    files_to_process = []
    for cam in ['v2lis', 'eesuks']:
        log.debug(f'Working on cam {cam}.')
        main_path = f'/@Timelapse/{cam} timelapse'
        folders = conn.listPath(service_name=svc_name, path=main_path, pattern='20*')
        folders.reverse()
        # Hit the last 2 folders to ensure we're always getting at least 1 completed file
        for folder in folders[:2]:
            folder_name = folder.filename
            log.debug(f'In folder {folder_name}.')
            files = conn.listPath(service_name=svc_name, path=f'{main_path}/{folder_name}', pattern='*.mp4')
            for file in files:
                file_name = file.filename
                log.debug(f'On file {file_name}')
                time_diff = now_ts - file.last_write_time
                log.debug(f'Time diff is {time_diff}')
                if time_diff > 500:
                    log.debug('Logging file to extract list.')
                    full_path = f'{main_path}/{folder_name}/{file_name}'
                    files_to_process.append(full_path)
    return files_to_process


@influx.influx_exception_decorator(logger=log)
def post_to_slack(files_to_process: List[str], conn: SMBConnection, svc_name: str):
    log.debug('Initializing Slack comm.')
    sc = SlackComm()
    timestamp_pattern = re.compile(r'-(\d+).mp4')
    log.debug(f'{len(files_to_process)} file to process.')
    for file in files_to_process:
        log.debug(f'Working on {file}')
        # Get the timestamp it was created
        timestamp = float(timestamp_pattern.search(file).group(1))
        log.debug(f'Timestamp for file is {timestamp}')
        if timestamp - 500 > last_time:
            log.debug('Ts - 500 was greater than last_time... Attempting to save file and post to slack.')
            try:
                with tempfile.NamedTemporaryFile(mode='wb', buffering=1024) as file_obj:
                    attr, size = conn.retrieveFile(service_name=svc_name, path=file, file_obj=file_obj)
                    sc.st.upload_file(sc.kaamerate_kanal, file_obj.name, file.split('/')[-1])
                    log.info('Message likely posted to slack')
            except Exception as e:
                log.exception(e)
        else:
            log.debug('Bypassed file.')


# Try to get a variable representing the last time a scan was done
last_time_path = Path().home().joinpath('data/last_time_timelapse')
if not last_time_path.exists():
    last_time_path.parent.mkdir(parents=True, exist_ok=True)
    last_time = 0
else:
    log.debug('Reading last read timestamp from path')
    with last_time_path.open() as f:
        last_time = float(f.read().strip())

now_ts = datetime.now().timestamp()

conn, svc_name = connect_to_smb()
files_to_process = get_files(conn=conn, svc_name=svc_name)

post_to_slack(files_to_process, conn, svc_name)

log.debug('Writing current timestamp to file.')
last_time_path.touch(exist_ok=True)
with last_time_path.open(mode='w') as f:
    f.write(str(now_ts))
log.info('Done.')
