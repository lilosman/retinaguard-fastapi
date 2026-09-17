import paramiko, io, tarfile, os, sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HOST='141.140.0.233'; USER='root'; PASS='0Ye762tFihRPD3w'
BACKEND=r'F:\OSMAN-My-Github\retinaguard-fastapi\python-api'

def ssh(c, cmd, timeout=30):
    _,o,e = c.exec_command(cmd, timeout=timeout)
    out = (o.read().decode('utf-8','replace')+e.read().decode('utf-8','replace')).strip()
    safe = out[-400:].encode('ascii','replace').decode()
    if safe: print(f'  {safe}')
    return out

def make_tar(src, excl):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as t:
        for root,dirs,files in os.walk(src):
            dirs[:] = [d for d in dirs if d not in excl]
            for f in files:
                fp = os.path.join(root,f)
                t.add(fp, arcname=os.path.relpath(fp,src))
    buf.seek(0)
    return buf

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PASS, timeout=20)
print('[OK] Connected')

# 1. Upload fixed backend
sftp = c.open_sftp()
print('[1] Uploading fixed backend (ThreadPool + no duplicate routes)...')
sftp.putfo(make_tar(BACKEND, ['venv','__pycache__','.git']), '/tmp/be.tar.gz')
ssh(c, 'cd /opt/retinaguard/python-api && tar xzf /tmp/be.tar.gz && echo "Backend uploaded OK"')
sftp.close()

# 2. Restart backend container only (no rebuild needed)
print('\n[2] Restarting backend container...')
ssh(c, 'docker restart retinaguard-backend', timeout=30)
print('  Restarted! Waiting for TF to load (~60s)...')

# 3. Wait for startup then test
time.sleep(60)

print('\n[3] Container status:')
ssh(c, "docker ps --format '{{.Names}} {{.Status}}'")

print('\n[4] Backend logs:')
ssh(c, 'docker logs retinaguard-backend --tail 10 2>&1')

print('\n[5] Health check:')
ssh(c, 'curl -s --max-time 15 http://localhost:8000/health')

print('\n[6] Register test:')
ssh(c, """curl -s --max-time 15 -X POST http://localhost:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"name":"Demo","age":30,"gender":"Male","email":"demo_final@test.com","password":"Demo1234!"}' """)

print('\n[7] Login test (should get 403 needsVerification):')
ssh(c, """curl -s --max-time 10 -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo_final@test.com","password":"Demo1234!"}' """)

print('\nDone!')
c.close()
