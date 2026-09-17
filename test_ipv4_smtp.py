import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('141.140.0.233', username='root', password='0Ye762tFihRPD3w', timeout=15)

test_script = """
import socket

# Test with IPv4 specifically
ipv4_addresses = socket.getaddrinfo('smtp.gmail.com', 465, socket.AF_INET)
for item in ipv4_addresses[:2]:
    ip = item[4][0]
    print(f'Trying IPv4 {ip}:465')
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(4)
    try:
        s.connect((ip, 465))
        print(f'Connect to IPv4 {ip}:465 SUCCESS!')
        s.close()
    except Exception as e:
        print(f'Connect to IPv4 {ip}:465 FAILED: {e}')

# Test port 587
for item in socket.getaddrinfo('smtp.gmail.com', 587, socket.AF_INET)[:2]:
    ip = item[4][0]
    print(f'Trying IPv4 {ip}:587')
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(4)
    try:
        s.connect((ip, 587))
        print(f'Connect to IPv4 {ip}:587 SUCCESS!')
        s.close()
    except Exception as e:
        print(f'Connect to IPv4 {ip}:587 FAILED: {e}')
"""

stdin, stdout, stderr = c.exec_command(f"python3 -c \"{test_script}\"")
print(stdout.read().decode())
print(stderr.read().decode())
c.close()
