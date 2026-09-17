import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('141.140.0.233', username='root', password='0Ye762tFihRPD3w', timeout=15)

test_script = """
import requests, io
from PIL import Image

# Generate synthetic retinal fundus-like image
img = Image.new('RGB', (224, 224), color=(140, 70, 45))
buf = io.BytesIO()
img.save(buf, format='JPEG')
buf.seek(0)

r = requests.post('http://localhost:8000/predict', files={
    'image': ('fundus.jpg', buf, 'image/jpeg')
}, timeout=60)

print('PREDICT STATUS:', r.status_code)
if r.status_code == 200:
    d = r.json()
    print('PREDICTION:', d.get('prediction'))
    print('RISK LEVEL:', d.get('riskLevel'))
    print('PROBABILITY:', d.get('probability'))
    print('HAS HEATMAP:', bool(d.get('heatmapBase64')))
else:
    print('PREDICT ERROR:', r.text[:200])
"""

# Run inside the backend container where PIL and all dependencies are installed
stdin, stdout, stderr = c.exec_command(f"docker exec retinaguard-backend python3 -c \"{test_script}\"")
print(stdout.read().decode())
print(stderr.read().decode())
c.close()
