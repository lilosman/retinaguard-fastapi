from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from config import settings
from database import get_collection
from bson import ObjectId

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# 1. تشفير ومطابقة كلمة السر
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# 2. إنشاء JWT Token
def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# 3. التحقق من التوكن واستخراج المستخدم الحالي بمرونة تامة (بدون إيقاف الرفع)
async def get_current_user(token: str = Depends(oauth2_scheme)):
    if not token:
        return None

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub") or payload.get("userId")
        if not user_id:
            return None

        users_collection = get_collection("users")
        try:
            user = await users_collection.find_one({"_id": ObjectId(user_id)})
        except Exception:
            user = await users_collection.find_one({"_id": user_id})

        if user:
            user["_id"] = str(user["_id"])
            return user
        return None

    except Exception:
        # إذا كان التوكن قديماً أو غير صالح، لا نوقف العملية بل نعتبره Guest
        return None