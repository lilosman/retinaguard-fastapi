import paramiko
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HOST = "141.140.0.233"
USER = "root"
PASS = "0Ye762tFihRPD3w"

def ssh_run(client, cmd, timeout=30):
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    result = (out + " " + err).strip()
    safe = result[-400:].encode('ascii', errors='replace').decode('ascii')
    if safe: print(f"    {safe}")
    return result

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=20)
print("[OK] Connected to VPS")

# شغّل البناء في الخلفية بـ nohup
print("\n[1/2] Starting Docker build in background on VPS...")
build_script = """#!/bin/bash
cd /opt/retinaguard
docker compose down --remove-orphans 2>/dev/null
docker compose build --no-cache >> /opt/retinaguard/build.log 2>&1
docker compose up -d >> /opt/retinaguard/build.log 2>&1
echo "BUILD_COMPLETE" >> /opt/retinaguard/build.log
"""
with paramiko.SSHClient() as c2:
    c2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c2.connect(HOST, username=USER, password=PASS, timeout=20)
    sftp2 = c2.open_sftp()
    with sftp2.open('/opt/retinaguard/build.sh', 'w') as f:
        f.write(build_script)
    sftp2.close()
    c2.exec_command("chmod +x /opt/retinaguard/build.sh && nohup /opt/retinaguard/build.sh > /dev/null 2>&1 &")
    print("  Build started in background!")

print("\n[2/2] Checking build progress (checking every 30s)...")
for i in range(30):  # max 15 mins
    time.sleep(30)
    try:
        result = ssh_run(client, "tail -5 /opt/retinaguard/build.log 2>/dev/null || echo 'No log yet'")
        print(f"\n  [{i*30}s] Build log:")
        
        # Check if done
        done = ssh_run(client, "grep -c 'BUILD_COMPLETE' /opt/retinaguard/build.log 2>/dev/null || echo 0")
        if '1' in done:
            print("\n  BUILD COMPLETE!")
            break
            
        # Check containers
        containers = ssh_run(client, "docker ps --format '{{.Names}} {{.Status}}' 2>/dev/null")
        if 'retinaguard-backend' in containers:
            print(f"  Containers running: {containers}")
            break
    except Exception as e:
        print(f"  Reconnecting... ({e})")
        try:
            client.connect(HOST, username=USER, password=PASS, timeout=20)
        except:
            pass

print("\nFinal status:")
ssh_run(client, "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'")
ssh_run(client, "tail -10 /opt/retinaguard/build.log 2>/dev/null")

print(f"\n{'='*55}")
print(f"  Backend:  http://{HOST}:8000/health")
print(f"  Frontend: http://{HOST}")
print(f"{'='*55}")
client.close()
