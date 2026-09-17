import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('141.140.0.233', username='root', password='0Ye762tFihRPD3w', timeout=15)

script = """
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check():
    client = AsyncIOMotorClient('mongodb+srv://retinaguard:retina2026@cluster0.xu7mdt8.mongodb.net/retinaguard_fastapi_db?retryWrites=true&w=majority')
    db = client['retinaguard_fastapi_db']
    users = await db['users'].find({}, {'email': 1, 'role': 1, 'isVerified': 1, 'createdAt': 1}).sort('createdAt', -1).to_list(length=10)
    for u in users:
        print(u)

asyncio.run(check())
"""

stdin, stdout, stderr = c.exec_command(f"docker exec retinaguard-backend python3 -c \"{script}\"")
print(stdout.read().decode())
print(stderr.read().decode())
c.close()
