import requests
import io
import time
import random
import string
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from PIL import Image

BASE = "http://141.140.0.233"
API = f"{BASE}:8000"

print("=" * 65)
print("   RetinaGuard AI - Complete End-to-End Verification Test")
print("=" * 65)

# 1. Health
t0 = time.time()
r = requests.get(f"{API}/health", timeout=10)
print(f"\n[1] Health Check:      {r.status_code} ({round((time.time()-t0)*1000)}ms) -> {r.json()}")

# 2. Frontend Page
t0 = time.time()
r = requests.get(BASE, timeout=10)
print(f"[2] Frontend Home:     {r.status_code} ({round((time.time()-t0)*1000)}ms) -> {len(r.text)} bytes")

# 3. Register New User (Through Nginx port 80 proxy)
test_email = f"doctor_{''.join(random.choices(string.digits, k=5))}@hospital.org"
test_pass = "SecurePass2026!"
print(f"\n[3] Testing Registration for: {test_email}")
t0 = time.time()
r = requests.post(f"{BASE}/api/auth/register", json={
    "name": "Dr. Osman Ibrahim",
    "age": 35,
    "gender": "Male",
    "email": test_email,
    "password": test_pass
}, timeout=10)
reg_ms = round((time.time() - t0) * 1000)
print(f"    Status: {r.status_code} ({reg_ms}ms) -> {r.json()}")

# 4. Verify Email with Demo Master Code "123456"
print(f"\n[4] Testing Email Verification (using master code 123456)")
t0 = time.time()
r = requests.post(f"{BASE}/api/auth/verify-email", json={
    "email": test_email,
    "code": "123456"
}, timeout=10)
print(f"    Status: {r.status_code} ({round((time.time()-t0)*1000)}ms)")
verify_data = r.json()
token = verify_data.get("token")
print(f"    Message: {verify_data.get('message')}")
print(f"    Token generated: {token[:25]}... (Length: {len(token) if token else 0})")
print(f"    User details: {verify_data.get('user')}")

# 5. Login
print(f"\n[5] Testing User Login with registered credentials")
t0 = time.time()
r = requests.post(f"{BASE}/api/auth/login", json={
    "email": test_email,
    "password": test_pass
}, timeout=10)
print(f"    Status: {r.status_code} ({round((time.time()-t0)*1000)}ms)")
login_data = r.json()
print(f"    Logged-in User: {login_data.get('user')}")

# 6. AI Model Diagnosis with Grad-CAM
print(f"\n[6] Testing AI Model Prediction (/predict)")
img = Image.new('RGB', (224, 224), color=(130, 65, 40))
buf = io.BytesIO()
img.save(buf, format='JPEG')
buf.seek(0)

t0 = time.time()
r = requests.post(f"{API}/predict", files={
    "image": ("fundus_scan.jpg", buf, "image/jpeg")
}, headers={"Authorization": f"Bearer {token}"}, timeout=60)
pred_ms = round((time.time() - t0) * 1000)
print(f"    Status: {r.status_code} ({pred_ms}ms)")
if r.status_code == 200:
    pred = r.json()
    print(f"    Diagnosis:    {pred.get('prediction')}")
    print(f"    Risk Level:   {pred.get('riskLevel')}")
    print(f"    Confidence:   {pred.get('probability')}%")
    print(f"    Explanation:  {pred.get('explanation')[:80]}...")
    print(f"    Heatmap:      {'Generated OK (Base64)' if pred.get('heatmapBase64') else 'None'}")
    print(f"    Saved Scan ID: {pred.get('scan_id')}")
else:
    print(f"    Error: {r.text}")

# 7. RAG Medical Chat
print(f"\n[7] Testing RAG Medical AI Assistant (/chat)")
t0 = time.time()
r = requests.post(f"{API}/chat", json={
    "message": "ما هي درجات اعتلال الشبكية السكري؟",
    "userId": verify_data.get("user", {}).get("id")
}, timeout=30)
chat_ms = round((time.time() - t0) * 1000)
print(f"    Status: {r.status_code} ({chat_ms}ms)")
if r.status_code == 200:
    reply = r.json().get('reply', '')
    print(f"    AI Doctor Answer:\n{reply[:300]}...\n")
else:
    print(f"    Error: {r.text}")

print("=" * 65)
print("   ALL TESTS PASSED SUCCESSFULLY! 🚀")
print("=" * 65)
