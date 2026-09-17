import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('141.140.0.233', username='root', password='0Ye762tFihRPD3w', timeout=15)

stdin, stdout, stderr = c.exec_command('docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"')
print("=== DOCKER PS ===")
print(stdout.read().decode('utf-8', errors='replace'))

stdin, stdout, stderr = c.exec_command('docker logs retinaguard-backend --tail 30')
print("=== BACKEND LOGS ===")
print(stdout.read().decode('utf-8', errors='replace'))
print(stderr.read().decode('utf-8', errors='replace'))

c.close()
