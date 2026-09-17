import paramiko, sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('141.140.0.233', username='root', password='0Ye762tFihRPD3w', timeout=20)

def ssh(cmd, timeout=60):
    _,o,e = c.exec_command(cmd, timeout=timeout)
    out = (o.read().decode('utf-8','replace') + e.read().decode('utf-8','replace')).strip()
    safe = out[-500:].encode('ascii','replace').decode()
    if safe: print(safe)
    return out

print("="*55)
print("  RetinalGuard - System Test from VPS")
print("="*55)

print("\n[1] Health:")
ssh("curl -s --max-time 30 http://localhost:8000/health")

print("\n[2] Register new user:")
ssh("""curl -s --max-time 20 -X POST http://localhost:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"name":"Ahmed","age":30,"gender":"Male","email":"ahmedtest999@gmail.com","password":"Test1234!"}' """)

print("\n[3] Login (unverified - should get 403 needsVerification):")
ssh("""curl -s --max-time 10 -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"ahmedtest999@gmail.com","password":"Test1234!"}' """)

print("\n[4] Login with wrong password (should get 401):")
ssh("""curl -s --max-time 10 -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"ahmedtest999@gmail.com","password":"WRONGPASS"}' """)

print("\n[5] AI Model predict (real image - up to 60s):")
# Create a small test image
ssh("""python3 -c "
from PIL import Image
import io, base64
img = Image.new('RGB',(224,224),(100,60,40))
buf = io.BytesIO()
img.save(buf,'JPEG')
buf.seek(0)
open('/tmp/test_eye.jpg','wb').write(buf.read())
print('Image created')
" """)
ssh("curl -s --max-time 120 -X POST http://localhost:8000/predict -F 'image=@/tmp/test_eye.jpg' | python3 -c \"import sys,json; d=json.load(sys.stdin); print('riskLevel:', d.get('riskLevel'), '| prob:', d.get('probability'))\"", timeout=130)

print("\n[6] RAG Chat:")
ssh("""curl -s --max-time 45 -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"What is diabetic retinopathy?","userId":"test"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('reply','')[:120])" """, timeout=50)

print("\n[7] Nginx proxy (port 80 -> 8000):")
ssh("curl -s --max-time 20 http://localhost/api/auth/login -X POST -H 'Content-Type: application/json' -d '{\"email\":\"x@x.com\",\"password\":\"x\"}' | head -c 80")

print("\n" + "="*55)
print("  TEST COMPLETE")
print("="*55)
c.close()
