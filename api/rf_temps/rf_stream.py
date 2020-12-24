import subprocess
from kavalkilu import LogWithInflux, HOME_SERVER_HOSTNAME, Hosts


logg = LogWithInflux('rf_stream', log_dir='rf')
serv_ip = Hosts().get_ip_from_host(HOME_SERVER_HOSTNAME)
cmd = ['/usr/local/bin/rtl_433', '-F', f'syslog:{serv_ip}:1433']

logg.info(f'Sending command: {" ".join(cmd)}')
process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
process_output, _ = process.communicate()
logg.debug(f'Process output: {process_output}')
