import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('141.140.0.233', username='root', password='0Ye762tFihRPD3w', timeout=15)

stdin, stdout, stderr = c.exec_command('curl -s ipinfo.io/json')
print(stdout.read().decode())
print(stderr.read().decode())
c.close()
