import paramiko
import os
import tarfile
import io

HOST = "141.140.0.233"
USER = "root"
PASS = "0Ye762tFihRPD3w"

BACKEND_DIR  = r"F:\OSMAN-My-Github\retinaguard-fastapi\python-api"
FRONTEND_DIR = r"F:\os\Graduation project\front-end\artifacts\retinaguard"
COMPOSE_FILE = r"F:\OSMAN-My-Github\retinaguard-fastapi\docker-compose.yml"

def ssh_run(client, cmd):
    print(f"  $ {cmd[:90]}")
    _, stdout, stderr = client.exec_command(cmd, timeout=600, get_pty=True)
    out = stdout.read().decode(errors='replace').strip()
    if out: print(f"    {out[-400:]}")
    return out

def make_tar_gz(src_dir, excludes):
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

print("\n[1/7] Connecting to VPS...")
client.connect(HOST, username=USER, password=PASS, timeout=20)
print("  OK Connected!")

print("\n[2/7] Installing Docker on VPS...")
ssh_run(client, "which docker || (curl -fsSL https://get.docker.com | sh)")
ssh_run(client, "systemctl start docker; systemctl enable docker; docker --version")

print("\n[3/7] Creating project directories...")
ssh_run(client, "mkdir -p /opt/retinaguard/python-api /opt/retinaguard/frontend")

sftp = client.open_sftp()

print("\n[4/7] Packaging & uploading BACKEND (model 35MB included)...")
be_tar = make_tar_gz(BACKEND_DIR, excludes=['venv','__pycache__','.git','*.pyc'])
sftp.putfo(be_tar, "/tmp/backend.tar.gz")
print("  Backend uploaded!")
ssh_run(client, "cd /opt/retinaguard/python-api && tar xzf /tmp/backend.tar.gz && ls -la | head -15")

print("\n[5/7] Packaging & uploading FRONTEND...")
fe_tar = make_tar_gz(FRONTEND_DIR, excludes=['node_modules','dist','.git','.vite-temp'])
sftp.putfo(fe_tar, "/tmp/frontend.tar.gz")
print("  Frontend uploaded!")
ssh_run(client, "cd /opt/retinaguard/frontend && tar xzf /tmp/frontend.tar.gz && ls -la | head -10")

print("\n[6/7] Uploading docker-compose.yml...")
sftp.put(COMPOSE_FILE, "/opt/retinaguard/docker-compose.yml")
print("  docker-compose.yml uploaded!")
sftp.close()

print("\n[7/7] Building & launching Docker containers...")
print("  (This takes 5-10 minutes for TensorFlow install...)")
ssh_run(client, "cd /opt/retinaguard && docker compose down --remove-orphans 2>/dev/null; docker compose up --build -d 2>&1")

print("\nChecking running containers...")
ssh_run(client, "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'")

print("\n" + "="*55)
print(f"  DONE! Backend:  http://{HOST}:8000/health")
print(f"  DONE! Frontend: http://{HOST}")
print("="*55)
client.close()
