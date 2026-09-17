import paramiko, sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('141.140.0.233', username='root', password='0Ye762tFihRPD3w', timeout=20)

def ssh(cmd, timeout=20):
    _,o,e = c.exec_command(cmd, timeout=timeout)
    out = (o.read().decode('utf-8','replace') + e.read().decode('utf-8','replace')).strip()
    safe = out[-500:].encode('ascii','replace').decode()
    if safe: print(safe)
    return out

print('=== Container status ===')
ssh("docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'")

print('\n=== Backend last 25 logs ===')
ssh('docker logs retinaguard-backend --tail 25 2>&1')

print('\n=== Local health check (from VPS) ===')
ssh('curl -s --max-time 5 http://localhost:8000/health || echo TIMEOUT')

print('\n=== Local predict test (from VPS) ===')
ssh('curl -s --max-time 10 -X POST http://localhost:8000/predict -F "image=@/etc/hostname" -w "STATUS:%{http_code}" 2>&1 | tail -2')

c.close()
