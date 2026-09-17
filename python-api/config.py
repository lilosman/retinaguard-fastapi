import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 1. إعدادات المشروع العامة
    PROJECT_NAME: str = "RetinalGuard FastAPI Backend"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"

       # 2. إعدادات قاعدة البيانات (MongoDB Atlas)
    MONGODB_URI: str = os.getenv(
        "MONGODB_URI",
        "mongodb+srv://retinaguard:retina2026@cluster0.xu7mdt8.mongodb.net/retinaguard_fastapi_db?retryWrites=true&w=majority"
    )
    # غيّر اسم القاعدة هنا إلى اسم جديد تماماً:
    DATABASE_NAME: str = "retinaguard_fastapi_db"

    # 3. إعدادات التوكن والأمان (JWT)
    # قم بتغيير SECRET_KEY إلى أي نص عشوائي قوي خاص بك
    SECRET_KEY: str = os.getenv("SECRET_KEY", "YOUR_SUPER_SECRET_KEY_HERE_123456789_CHANGE_ME")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 أيام

    # 4. إعدادات موديل شبكية العين (AI Model)
    MODEL_PATH: str = os.getenv("MODEL_PATH", "model.h5")

    # 5. مفاتيح للـ RAG والذكاء الاصطناعي التوليدي
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "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")
    # 6. إعدادات البريد الإلكتروني
    EMAIL_USER: str = os.getenv("EMAIL_USER", "osmanibrahim6062@gmail.com")
    EMAIL_PASS: str = os.getenv("EMAIL_PASS", "cdabaitqldlpjwsv")
    
    class Config:
        env_file = ".env"
        extra = "ignore"

# إنشاء كائن سينمائي واحد لاستخدامه في كل المشروع
settings = Settings()