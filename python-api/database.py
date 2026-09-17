import sys
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings

# 1. إنشاء كائن الاتصال بقاعدة البيانات باستخدام الرابط المعرف في config.py
client = AsyncIOMotorClient(settings.MONGODB_URI)

# 2. تحديد اسم قاعدة البيانات
db = client[settings.DATABASE_NAME]

# 3. دالة فحص واختبار الاتصال (تستدعى عند بدء تشغيل تطبيق FastAPI)
async def connect_to_mongo():
    try:
        # إرسال ping لاختبار السيرفر
        await client.admin.command('ping')
        print(f"[OK] Connected to MongoDB Atlas successfully! Database: '{settings.DATABASE_NAME}'")
    except Exception as e:
        print(f"[ERROR] Failed to connect to MongoDB: {e}")

# 4. دالة إغلاق الاتصال عند إيقاف السيرفر
async def close_mongo_connection():
    client.close()
    print("[INFO] MongoDB connection closed.")

# 5. دوال سريعة للحصول على الـ Collections من أي مكان
def get_collection(collection_name: str):
    """
    دالة تساعدك للوصول لأي جدول/collection بسهولة.
    مثال:
    users_collection = get_collection("users")
    scans_collection = get_collection("scans")
    """
    return db[collection_name]