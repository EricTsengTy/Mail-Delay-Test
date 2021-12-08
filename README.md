# Mailing Delay Test
Generate mailing latency metrics for *prometheus* client

## Four-way Delay Test
* From **Outer (Gmail)** to **Inner SMTP Server**

* From **Outer (Gmail)** to **Inner GSuite**

* From **Inner SMTP Server** to **Outer (Gmail)**

* From **Inner Gsuite** to **Outer (Gmail)**

## Usage
```shell
$ ./mail-test.py -h
usage: mail-test.py [-h] [--daemon] [-f FILE] [-s]

External mailing test

optional arguments:
  -h, --help  show this help message and exit
  --daemon    run as daemon
  -f FILE     specify path of config file (default: /root/mail-test/mail-test.cfg)
  -s          signal the daemon by pid of daemon

Calculate delay of four different direction
```