from __future__ import print_function

import glob
import subprocess


def get_psql_conf_files(psql_conf_path=None):
    if psql_conf_path is None:
        psql_conf_path = '/etc/postgresql/*/main*/postgresql.conf'
    for fname_conf in glob.glob(psql_conf_path):
        yield fname_conf


def enable_psql_logs(psql_conf_path=None):
    """Enable psql logs.
    This change require receive from psql follow environment variables
    to start log. More info in get_env_log() method.
    """
    for fname_conf in get_psql_conf_files():
        with open(fname_conf, "a+") as fconf:
            if 'logging_collector = on\n' in fconf.readlines():
                continue
            print("Enable logs to", fname_conf)
            fconf.write("""
logging_collector = on
log_destination = 'stderr'
log_directory = 'pg_log'
log_filename = 'postgresql.log'
log_rotation_age = 0
log_checkpoints = on
log_hostname = on
log_line_prefix = '%t [%p]: [%l-1] db=%d,user=%u '""")
    subprocess.call("/etc/init.d/postgresql restart", shell=True)


def get_env_log(env=None):
    "Get environment variables to enable logs from client"
    if env is None:
        env = {}
    custom_env = env.copy()
    custom_env.setdefault('PGOPTIONS', '')
    custom_env['PGOPTIONS'] += " -c client_min_messages=notice -c log_min_messages=warning -c log_min_error_statement=error -c log_min_duration_statement=0 -c log_connections=on -c log_disconnections=on -c log_duration=off -c log_error_verbosity=verbose -c log_lock_waits=on -c log_statement=none -c log_temp_files=0"  # noqa
    custom_env['PGOPTIONS'] = custom_env['PGOPTIONS'].strip(' ')
    return custom_env


if __name__ == '__main__':
    enable_psql_logs()
