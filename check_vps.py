import paramiko, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('141.140.0.233', username='root', password='0Ye762tFihRPD3w', timeout=20)

def ssh(cmd):
    _, o, e = client.exec_command(cmd, timeout=15)
    out = (o.read().decode('utf-8', errors='replace') + e.read().decode('utf-8', errors='replace')).strip()
    safe = out[-600:].encode('ascii','replace').decode()
    if safe: print(safe)

print('=== Build Log (last 20 lines) ===')
ssh('tail -20 /opt/retinaguard/build.log 2>/dev/null')

print('\n=== Build script still running? ===')
ssh("ps aux | grep build.sh | grep -v grep || echo 'Build script done'")

print('\n=== Containers ===')
ssh("docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'")

print('\n=== Docker images ===')
ssh("docker images | grep retinaguard")

client.close()
