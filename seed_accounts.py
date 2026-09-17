import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('141.140.0.233', username='root', password='0Ye762tFihRPD3w', timeout=15)

script = """
import asyncio
from datetime import datetime
from database import get_collection
from auth_service import hash_password

async def setup():
    users = get_collection('users')
    hashed = hash_password('Password123!')
    
    accounts = [
        ('Osman Ibrahim', 'osmanibrahim6062@gmail.com', 'patient'),
        ('Demo Patient', 'demo@retinaguard.com', 'patient'),
        ('Dr. Sarah Smith', 'doctor@retinaguard.com', 'doctor'),
        ('Admin User', 'admin@retinaguard.com', 'admin'),
    ]
    
    for name, email, role in accounts:
        await users.delete_many({'email': email.lower()})
        doc = {
            'name': name,
            'email': email.lower(),
            'password': hashed,
            'role': role,
            'age': 30,
            'gender': 'Male',
            'isVerified': True,
            'createdAt': datetime.utcnow()
        }
        await users.insert_one(doc)
        print(f'[OK] Account ready: {email} | Password: Password123! | Role: {role}')

asyncio.run(setup())
"""

stdin, stdout, stderr = c.exec_command(f"docker exec -w /app retinaguard-backend python3 -c \"{script}\"")
print(stdout.read().decode())
print(stderr.read().decode())
c.close()
