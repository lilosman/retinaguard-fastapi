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

BACKEND_DIR = r"F:\OSMAN-My-Github\retinaguard-fastapi\python-api"
FRONTEND_DIST = r"F:\os\Graduation project\front-end\artifacts\retinaguard\dist\public"
FRONTEND_NGINX = r"F:\os\Graduation project\front-end\artifacts\retinaguard\nginx.conf"

def ssh(c, cmd, timeout=30):
    _, o, e = c.exec_command(cmd, timeout=timeout)
    out = (o.read().decode('utf-8', 'replace') + e.read().decode('utf-8', 'replace')).strip()
    safe = out[-400:].encode('ascii', 'replace').decode()
    if safe: print(f"  {safe}")
    return out

def make_tar_from_files(files_dict):
    """files_dict: {arcname: local_path}"""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as t:
        for arcname, local_path in files_dict.items():
            if os.path.isfile(local_path):
                t.add(local_path, arcname=arcname)
            elif os.path.isdir(local_path):
                for root, dirs, files in os.walk(local_path):
                    for f in files:
                        fp = os.path.join(root, f)
                        rel = os.path.relpath(fp, local_path)
                        t.add(fp, arcname=os.path.join(arcname, rel))
    buf.seek(0)
    return buf

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PASS, timeout=20)
print("[OK] Connected to VPS")

sftp = c.open_sftp()

# 1. Upload backend python files
print("\n[1/4] Uploading backend files...")
be_files = {
    "main.py": os.path.join(BACKEND_DIR, "main.py"),
    "email_service.py": os.path.join(BACKEND_DIR, "email_service.py"),
    "config.py": os.path.join(BACKEND_DIR, "config.py"),
    "rag_service.py": os.path.join(BACKEND_DIR, "rag_service.py"),
    "auth_service.py": os.path.join(BACKEND_DIR, "auth_service.py"),
}
be_tar = make_tar_from_files(be_files)
sftp.putfo(be_tar, "/tmp/be_update.tar.gz")
ssh(c, "cd /opt/retinaguard/python-api && tar xzf /tmp/be_update.tar.gz")
ssh(c, "docker cp /opt/retinaguard/python-api/main.py retinaguard-backend:/app/main.py")
ssh(c, "docker cp /opt/retinaguard/python-api/email_service.py retinaguard-backend:/app/email_service.py")
ssh(c, "docker cp /opt/retinaguard/python-api/config.py retinaguard-backend:/app/config.py")
ssh(c, "docker cp /opt/retinaguard/python-api/rag_service.py retinaguard-backend:/app/rag_service.py")
ssh(c, "docker cp /opt/retinaguard/python-api/auth_service.py retinaguard-backend:/app/auth_service.py")
print("  Backend files injected into container!")

# 2. Upload frontend dist
print("\n[2/4] Uploading frontend dist...")
fe_files = {
    "public": FRONTEND_DIST,
    "nginx.conf": FRONTEND_NGINX
}
fe_tar = make_tar_from_files(fe_files)
sftp.putfo(fe_tar, "/tmp/fe_update.tar.gz")
ssh(c, "mkdir -p /opt/retinaguard/frontend/dist && cd /opt/retinaguard/frontend/dist && tar xzf /tmp/fe_update.tar.gz")
ssh(c, "docker cp /opt/retinaguard/frontend/dist/public/. retinaguard-frontend:/usr/share/nginx/html/")
ssh(c, "docker cp /opt/retinaguard/frontend/dist/nginx.conf retinaguard-frontend:/etc/nginx/conf.d/default.conf")
ssh(c, "docker exec retinaguard-frontend nginx -s reload")
print("  Frontend updated and Nginx reloaded!")

# 3. Update docker-compose.yml on host with volumes
print("\n[3/4] Updating docker-compose.yml...")
compose_content = """version: '3.9'
services:
  backend:
    build:
      context: ./python-api
      dockerfile: Dockerfile
    container_name: retinaguard-backend
    restart: always
    ports:
      - "8000:8000"
    volumes:
      - ./python-api:/app
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
    volumes:
      - ./frontend/dist/public:/usr/share/nginx/html
      - ./frontend/nginx.conf:/etc/nginx/conf.d/default.conf
    depends_on:
      - backend
    networks:
      - retina_net

networks:
  retina_net:
    driver: bridge
"""
with sftp.open("/opt/retinaguard/docker-compose.yml", "w") as f:
    f.write(compose_content)
sftp.close()

# 4. Restart backend container to load updated code
print("\n[4/4] Restarting backend container...")
ssh(c, "docker restart retinaguard-backend")
print("  Waiting 20s for Uvicorn and model startup...")
time.sleep(20)

# Check status
print("\n=== SYSTEM HEALTH CHECK ===")
ssh(c, "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'")
ssh(c, "docker logs retinaguard-backend --tail 10")

c.close()
print("\n[OK] Deployment complete!")
