import paramiko, sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('141.140.0.233', username='root', password='0Ye762tFihRPD3w', timeout=20)

def ssh(cmd, timeout=30):
    _, o, e = client.exec_command(cmd, timeout=timeout)
    out = (o.read().decode('utf-8', errors='replace') + e.read().decode('utf-8', errors='replace')).strip()
    safe = out[-500:].encode('ascii','replace').decode()
    if safe: print(f"  {safe}")
    return out

print("[1] Starting containers...")
ssh("cd /opt/retinaguard && docker compose up -d 2>&1", timeout=60)

print("\n[2] Waiting 15s for startup...")
time.sleep(15)

print("\n[3] Container status:")
ssh("docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'")

print("\n[4] Backend logs:")
ssh("docker logs retinaguard-backend --tail 15 2>&1")

print("\n[5] Testing health endpoint:")
ssh("curl -s http://localhost:8000/health")

print("\n[6] Testing frontend:")
ssh("curl -s -o /dev/null -w '%{http_code}' http://localhost:80")

client.close()
print("\nDone!")
