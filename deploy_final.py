import paramiko
import os
import tarfile
import io
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HOST = "141.140.0.233"
USER = "root"
PASS = "0Ye762tFihRPD3w"

BACKEND_DIR  = r"F:\OSMAN-My-Github\retinaguard-fastapi\python-api"
FRONTEND_DIR = r"F:\os\Graduation project\front-end\artifacts\retinaguard"

def ssh(client, cmd, timeout=30):
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    result = (out + "\n" + err).strip()
    if result:
        safe = result[-300:].encode('ascii', errors='replace').decode('ascii')
        print(f"  {safe}")
    return result

def make_tar(src_dir, excludes):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as tar:
        for root, dirs, files in os.walk(src_dir):
            dirs[:] = [d for d in dirs if d not in excludes]
            for f in files:
                fp = os.path.join(root, f)
                arc = os.path.relpath(fp, src_dir)
                tar.add(fp, arcname=arc)
    buf.seek(0)
    return buf

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=20)
print("[OK] Connected to VPS\n")

sftp = client.open_sftp()

# 1. Upload backend (with auth endpoints)
print("[1/4] Uploading backend (with auth endpoints)...")
be_tar = make_tar(BACKEND_DIR, excludes=['venv','__pycache__','.git'])
sftp.putfo(be_tar, "/tmp/backend.tar.gz")
ssh(client, "rm -rf /opt/retinaguard/python-api && mkdir -p /opt/retinaguard/python-api && cd /opt/retinaguard/python-api && tar xzf /tmp/backend.tar.gz && echo 'Backend OK'")

# 2. Upload frontend (pre-built dist + nginx with /api proxy)
print("\n[2/4] Uploading frontend (with /api proxy nginx)...")
fe_tar = make_tar(FRONTEND_DIR, excludes=['node_modules','.git','.vite-temp'])
sftp.putfo(fe_tar, "/tmp/frontend.tar.gz")
ssh(client, "rm -rf /opt/retinaguard/frontend && mkdir -p /opt/retinaguard/frontend && cd /opt/retinaguard/frontend && tar xzf /tmp/frontend.tar.gz && echo 'Frontend OK'")

# 3. Write docker-compose (with backend hostname for nginx proxy)
print("\n[3/4] Writing docker-compose.yml...")
compose = """version: '3.9'
services:
  backend:
    build:
      context: ./python-api
      dockerfile: Dockerfile
    container_name: retinaguard-backend
    restart: always
    ports:
      - "8000:8000"
    environment:
      - MODEL_PATH=/app/output/efficientnetb0_blindness_model.keras
      - VECTORSTORE_PATH=/app/vectorstore
      - TF_CPP_MIN_LOG_LEVEL=3
      - TF_ENABLE_ONEDNN_OPTS=0
    networks:
      - retina_net

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: retinaguard-frontend
    restart: always
    ports:
      - "80:80"
    depends_on:
      - backend
    networks:
      - retina_net

networks:
  retina_net:
    driver: bridge
"""
with sftp.open("/opt/retinaguard/docker-compose.yml", "w") as f:
    f.write(compose)
sftp.close()
print("  docker-compose.yml OK")

# 4. Rebuild and restart only changed containers
print("\n[4/4] Restarting Docker containers...")

# Write build script
build_sh = """#!/bin/bash
cd /opt/retinaguard
docker compose down --remove-orphans 2>/dev/null
docker compose build --no-cache >> /opt/retinaguard/build.log 2>&1
docker compose up -d >> /opt/retinaguard/build.log 2>&1
echo "BUILD_DONE" >> /opt/retinaguard/build.log
"""
with paramiko.SSHClient() as c2:
    c2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c2.connect(HOST, username=USER, password=PASS, timeout=20)
    sftp2 = c2.open_sftp()
    with sftp2.open('/opt/retinaguard/build.sh', 'w') as f:
        f.write(build_sh)
    sftp2.close()
    c2.exec_command("chmod +x /opt/retinaguard/build.sh && echo '' > /opt/retinaguard/build.log && nohup /opt/retinaguard/build.sh > /dev/null 2>&1 &")
    print("  Build started in background (5-10 mins)...")

print("\nMonitoring build progress...")
for i in range(25):
    time.sleep(30)
    try:
        result = ssh(client, "tail -3 /opt/retinaguard/build.log 2>/dev/null")
        done = ssh(client, "grep -c BUILD_DONE /opt/retinaguard/build.log 2>/dev/null || echo 0")
        if '1' in done:
            print(f"\n  BUILD COMPLETE after {(i+1)*30}s!")
            break
        running = ssh(client, "docker ps --format '{{.Names}}' 2>/dev/null")
        if 'retinaguard-backend' in running:
            print(f"\n  Containers UP!")
            break
    except Exception:
        client.connect(HOST, username=USER, password=PASS, timeout=20)

print("\n=== FINAL STATUS ===")
ssh(client, "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'")
ssh(client, "docker logs retinaguard-backend --tail 8 2>&1")

print(f"\n{'='*55}")
print(f"  Frontend:  http://{HOST}")
print(f"  Backend:   http://{HOST}:8000/health")
print(f"  API Docs:  http://{HOST}:8000/docs")
print(f"{'='*55}")
client.close()
