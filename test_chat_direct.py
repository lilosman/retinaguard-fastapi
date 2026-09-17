import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('141.140.0.233', username='root', password='0Ye762tFihRPD3w', timeout=15)

test_script = """
import requests

# Test 1: Chat endpoint
r = requests.post('http://localhost:8000/chat', json={
    'message': 'ما هو اعتلال الشبكية السكري باختصار؟',
    'userId': 'test'
}, timeout=30)
print('CHAT STATUS:', r.status_code)
if r.status_code == 200:
    print('CHAT REPLY:', r.json().get('reply', '')[:200])
else:
    print('CHAT ERROR:', r.text[:200])
"""

stdin, stdout, stderr = c.exec_command(f"python3 -c \"{test_script}\"")
print(stdout.read().decode())
print(stderr.read().decode())
c.close()
