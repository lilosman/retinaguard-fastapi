import requests, io, sys, json, random, string, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = "http://141.140.0.233"
API  = f"{BASE}:8000"
ok = []
fail = []

def check(name, passed, detail=""):
    if passed:
        ok.append(name)
        print(f"  PASS  {name} {detail}")
    else:
        fail.append(name)
        print(f"  FAIL  {name} {detail}")

print("="*60)
print("   RetinalGuard Full System Test")
print("="*60)

# 1. Health
try:
    r = requests.get(f"{API}/health", timeout=10)
    d = r.json()
    check("Backend Health", r.status_code==200 and "healthy" in d.get("status",""), str(d))
except Exception as e:
    check("Backend Health", False, str(e))

# 2. Frontend
try:
    r = requests.get(BASE, timeout=10)
    check("Frontend (Nginx)", r.status_code==200, f"({len(r.text)} bytes)")
except Exception as e:
    check("Frontend (Nginx)", False, str(e))

# 3. Nginx /api proxy
try:
    r = requests.get(f"{BASE}/api/nonexistent", timeout=5)
    check("Nginx /api Proxy", r.status_code in [404,405,422], f"proxy works ({r.status_code})")
except Exception as e:
    check("Nginx /api Proxy", False, str(e))

# 4. Register new user
email = f"test{''.join(random.choices(string.digits,k=6))}@retinaguard.com"
password = "TestPass123!"
try:
    r = requests.post(f"{BASE}/api/auth/register", json={
        "name": "Test User", "age": 28, "gender": "Male",
        "email": email, "password": password
    }, timeout=15)
    d = r.json()
    msg = d.get("message","") or d.get("token","")[:20]+"..."
    check("Register New User", r.status_code==200, f"({msg[:50]})")
    registered = True
except Exception as e:
    check("Register New User", False, str(e))
    registered = False

# 5. Login with unverified user
if registered:
    try:
        r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": password}, timeout=10)
        d = r.json()
        if r.status_code == 403 and d.get("needsVerification"):
            check("Login -> Needs Verification (correct!)", True, "403 needsVerification=True")
        elif r.status_code == 200 and d.get("token"):
            check("Login (auto-verified)", True, "token returned")
        else:
            check("Login Flow", False, str(d)[:80])
    except Exception as e:
        check("Login Flow", False, str(e))

# 6. Login with wrong password
try:
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": "WRONGPASS"}, timeout=10)
    check("Login Wrong Password (401)", r.status_code==401, f"({r.status_code})")
except Exception as e:
    check("Login Wrong Password", False, str(e))

# 7. Model prediction
try:
    from PIL import Image
    img = Image.new("RGB", (224,224), color=(120,70,50))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    r = requests.post(f"{API}/predict",
        files={"image": ("eye.jpg", buf, "image/jpeg")}, timeout=60)
    d = r.json()
    risk = d.get("riskLevel","")
    prob = d.get("probability","")
    check("AI Model (/predict)", r.status_code==200 and bool(risk), f"riskLevel={risk} prob={prob}%")
except Exception as e:
    check("AI Model (/predict)", False, str(e))

# 8. RAG Chat
try:
    r = requests.post(f"{API}/chat",
        json={"message": "What is diabetic retinopathy?", "userId": "test"},
        timeout=30)
    d = r.json()
    reply = d.get("reply","")
    check("RAG Chat (/chat)", r.status_code==200 and len(reply)>20, f"({len(reply)} chars)")
except Exception as e:
    check("RAG Chat (/chat)", False, str(e))

# 9. Scans endpoint
try:
    r = requests.get(f"{API}/api/scans/my",
        headers={"Authorization": "Bearer fake"}, timeout=10)
    check("Scans Endpoint", r.status_code in [200,401,403], f"({r.status_code})")
except Exception as e:
    check("Scans Endpoint", False, str(e))

print("\n" + "="*60)
print(f"   PASSED: {len(ok)}/{len(ok)+len(fail)}")
if fail:
    print(f"   FAILED: {', '.join(fail)}")
print("="*60)
print(f"\n  Frontend:  {BASE}")
print(f"  Backend:   {API}/docs")
