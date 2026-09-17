import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('141.140.0.233', username='root', password='0Ye762tFihRPD3w', timeout=15)

test_script = """
import socket

for port in [2525, 2526, 8025, 2025]:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)
    try:
        s.connect(('smtp.gmail.com', port))
        print(f'smtp.gmail.com:{port} SUCCESS')
        s.close()
    except Exception as e:
        print(f'smtp.gmail.com:{port} FAILED: {e}')
"""

stdin, stdout, stderr = c.exec_command(f"python3 -c \"{test_script}\"")
print(stdout.read().decode())
print(stderr.read().decode())
c.close()
