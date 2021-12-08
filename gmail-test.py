#!/usr/bin/env python3
from argparse import Namespace
from multiprocessing import Process, Manager
import time, datetime
import configparser
import argparse
import os
import signal

from mail.send import send_from_smtp
from mail.recv import recv_from_imap
from prometheus_client import start_http_server, Gauge, Info

# Config that store account & password
CONFIG_FILE = './gmail-test.cfg'
DESCRIPTION = 'External mailing test'
EPILOG = 'Calculate delay of four different direction'
DAEMON_PID_FILE = '/root/project/gmail-test/.pid'

# Object for sending and receiving test
class Task:
    # arg: [ send_addr, send_pass, recv_addr, recv_pass, smtp_server, imap_server ]
    def __init__(self, name, info, timestamp=''):
        self.name = name
        self.sendargs = {
            'send_addr': info[0],
            'send_pass': info[1],
            'recv_addr': info[2],
            'smtp_server': info[4],
            'subject': f'MAILTEST. {name} {timestamp}',
        }
        self.recvargs = {
            'recv_addr': info[2],
            'recv_pass': info[3],
            'send_addr': info[0],
            'imap_server': info[5],
            'subject': f'MAILTEST. {name} {timestamp}',
        }

'''#
Outer: Gmail
Inner: Csie mail server & G-suite
'''
config = Namespace(
    outer_addr = '',
    outer_pass = '',
    inner_addr = '',
    inner_pass = '',
    gmail_smtp = ('smtp.gmail.com', 587),
    csie_smtp  = ('smtp.csie.ntu.edu.tw', 587),
    gmail_imap = 'imap.gmail.com',
    csie_imap =  'imap.csie.ntu.edu.tw',
)

# Grab information from config file
def setup_config():
    fconfig = configparser.ConfigParser()
    fconfig.read(CONFIG_FILE)
    config.outer_addr = fconfig['MAILTEST']['outer_addr']
    config.outer_pass = fconfig['MAILTEST']['outer_pass']
    config.inner_addr = fconfig['MAILTEST']['inner_addr']
    config.inner_pass = fconfig['MAILTEST']['inner_pass']

def gettaskscfg():
    # Tasks config
    taskscfg = {
        'Gmail -> G-Suite': [
            config.outer_addr, # sender address
            config.outer_pass, # sender password
            config.inner_addr, # receiver address
            config.inner_pass, # receiver password
            config.gmail_smtp, # smtp of sender
            config.gmail_imap, # imap of receiver
        ],
        'Gmail -> SMTP': [
            config.outer_addr,
            config.outer_pass,
            config.inner_addr,
            config.inner_pass,
            config.gmail_smtp,
            config.csie_imap,
        ],
        'G-Suite -> Gmail': [
            config.inner_addr,
            config.inner_pass,
            config.outer_addr,
            config.outer_pass,
            config.gmail_smtp,
            config.gmail_imap,
        ],
        'SMTP -> Gmail': [
            config.inner_addr,
            config.inner_pass,
            config.outer_addr,
            config.outer_pass,
            config.csie_smtp,
            config.gmail_imap,
        ]
    }
    return taskscfg

# timeout: second(s)
def sequential_test(taskscfg, timeout=200, noreply=300):
    timestamp = str(int(time.time()))
    latency = dict.fromkeys(taskscfg.keys(), noreply)
    tasks = [ Task(task_name, arg, timestamp=timestamp) for task_name, arg in taskscfg.items() ]

    for task in tasks:
        send_from_smtp(**task.sendargs, content=timestamp)
        start_time = time.time()
        while time.time() - start_time <= timeout and latency[task.name] == noreply:
            latency[task.name] = time.time() - start_time if timestamp == recv_from_imap(**task.recvargs)[0] else noreply
            time.sleep((time.time() - start_time) / 10) # Sleep longer when waiting longer

    return latency

# Fake parallel
# timeout: second(s)
def parallel_test(taskscfg, timeout=200, noreply=300):
    timestamp = str(int(time.time()))
    latency = dict.fromkeys(taskscfg.keys(), noreply)
    tasks = [ Task(task_name, arg, timestamp=timestamp) for task_name, arg in taskscfg.items() ]

    for task in tasks:
        send_from_smtp(**task.sendargs, content=timestamp)

    start_time = time.time()
    for task in tasks:
        while time.time() - start_time <= timeout and latency[task.name] == noreply:
            latency[task.name] = time.time() - start_time if timestamp == recv_from_imap(**task.recvargs)[0] else noreply
            time.sleep((time.time() - start_time) / 10) # Sleep longer when waiting longer

    return latency

# Signal handler
def sighandler(signum, frame):
    return

# Mailing test (hourly)
def hourly_test(taskscfg, latency):
    # Set signal handler and write pid
    signal.signal(signal.SIGUSR1, sighandler)
    with open(DAEMON_PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

    # First Test
    latency.update(sequential_test(taskscfg, noreply=-20))

    while True:
        # Sleep until the time on the hour (Remove for debugging)
        # now = datetime.datetime.now()
        # next = now.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=1)
        # time.sleep((next - now).total_seconds())
        signal.pause()

        # Mailing Test
        latency.update(sequential_test(taskscfg, noreply=-20))
    

def setup_metrics(sample_information, key_to_prom_metrics):
    metrics_dict = {}
    for key in sample_information:
        metrics = key_to_prom_metrics[key]
        metrics_dict[metrics] = Gauge(metrics, metrics)
    return metrics_dict

def generate_metrics(latency, key_to_prom_metrics, metrics_dict):
    for key, value in latency.items():
        if value:
            metrics_dict[key_to_prom_metrics[key]].set(value)

# Prometheus client(?)
def prometheus(latency):
    start_http_server(9091)
    sample_information = {'Gmail -> G-Suite': None, 'Gmail -> SMTP': None, 'G-Suite -> Gmail': None, 'SMTP -> Gmail': None}
    key_to_prom_metrics = {'Gmail -> G-Suite': "Gmail_to_GSuite", 'Gmail -> SMTP': "Gmail_to_SMTP", 'G-Suite -> Gmail': "GSuite_to_Gmail", 'SMTP -> Gmail': "SMTP_to_Gmail"}
    metrics_dict = setup_metrics(sample_information, key_to_prom_metrics)

    while True:
        generate_metrics(latency, key_to_prom_metrics, metrics_dict)

# Main function
if __name__ == '__main__':
    # Parse arguments
    argparser = argparse.ArgumentParser(description=DESCRIPTION, epilog=EPILOG)
    argparser.add_argument('--daemon', action='store_true', help=f'run as daemon')
    argparser.add_argument('-f', metavar='FILE', action='store', default=CONFIG_FILE, type=str, help=f'specify path of config file (default: {CONFIG_FILE})')
    argparser.add_argument('-s', action='store_true', help=f'signal the daemon by pid of daemon')
    args = argparser.parse_args()
    CONFIG_FILE = args.f

    # Get test account config data
    setup_config()

    if args.daemon:
        # Get tasks configuration
        taskscfg = gettaskscfg()

        manager = Manager()
        # Latency for all tasks (None: not received)
        latency = manager.dict(dict.fromkeys(taskscfg.keys()))

        # Run mailing test and promethus
        p1 = Process(target=hourly_test, args=(taskscfg, latency))
        p2 = Process(target=prometheus, args=(latency,))
        p1.start()
        p2.start()

        p1.join()
        p2.join()
    
    elif args.s:
        with open(DAEMON_PID_FILE, 'r') as f:
            daemon_pid = int(f.read())
        print(f'Send signal to {daemon_pid}')
        os.kill(daemon_pid, signal.SIGUSR1)

    else:
        argparser.print_help()
