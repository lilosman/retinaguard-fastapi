import paramiko, io, tarfile, os, sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HOST = "141.140.0.233"
USER = "root"
PASS = "0Ye762tFihRPD3w"

BACKEND_DIR  = r"F:\OSMAN-My-Github\retinaguard-fastapi\python-api"
FRONTEND_DIR = r"F:\os\Graduation project\front-end\artifacts\retinaguard"

def ssh(client, cmd, timeout=30):
    _, o, e = client.exec_command(cmd, timeout=timeout)
    out = (o.read().decode('utf-8','replace') + e.read().decode('utf-8','replace')).strip()
    safe = out[-300:].encode('ascii','replace').decode()
    if safe: print(f"  {safe}")
    return out

def make_tar(src_dir, excludes):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as tar:
        for root, dirs, files in os.walk(src_dir):
            dirs[:] = [d for d in dirs if d not in excludes]
            for f in files:
                fp = os.path.join(root, f)
                tar.add(fp, arcname=os.path.relpath(fp, src_dir))
    buf.seek(0)
    return buf

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=20)
print("[OK] Connected\n")
sftp = client.open_sftp()

# 1. Upload new backend (fixed register/login)
print("[1/3] Uploading backend with fixed auth...")
be_tar = make_tar(BACKEND_DIR, excludes=['venv','__pycache__','.git'])
sftp.putfo(be_tar, "/tmp/backend_new.tar.gz")
ssh(client, "rm -rf /opt/retinaguard/python-api && mkdir -p /opt/retinaguard/python-api && cd /opt/retinaguard/python-api && tar xzf /tmp/backend_new.tar.gz && echo 'Backend OK'")

# 2. Upload new frontend (fixed auth flow + nginx proxy)
print("\n[2/3] Uploading frontend with fixed auth flow...")
fe_tar = make_tar(FRONTEND_DIR, excludes=['node_modules','.git','.vite-temp'])
sftp.putfo(fe_tar, "/tmp/frontend_new.tar.gz")
ssh(client, "rm -rf /opt/retinaguard/frontend && mkdir -p /opt/retinaguard/frontend && cd /opt/retinaguard/frontend && tar xzf /tmp/frontend_new.tar.gz && echo 'Frontend OK'")
sftp.close()

# 3. Restart only the containers (images already built = fast!)
print("\n[3/3] Restarting containers (using cached images)...")
ssh(client, "cd /opt/retinaguard && docker compose down && docker compose up --build -d 2>&1 | tail -10", timeout=120)

time.sleep(8)
print("\n=== Final Status ===")
ssh(client, "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'")
ssh(client, "curl -s http://localhost:8000/health")

# Quick auth test
print("\n=== Auth Test ===")
ssh(client, """curl -s -X POST http://localhost/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"name":"Test","age":25,"gender":"Male","email":"quicktest@test.com","password":"Test1234!"}' | head -c 100""")

print(f"\n  Frontend: http://{HOST}")
print(f"  Backend:  http://{HOST}:8000/docs")
client.close()
