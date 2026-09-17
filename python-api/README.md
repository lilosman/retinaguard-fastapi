# RetinalGuard — FastAPI AI Server

## 📁 الملفات

```
python-api/
├── main.py           ← السيرفر الرئيسي (FastAPI)
├── requirements.txt  ← المكتبات المطلوبة
└── model.h5          ← ضع موديلك هنا
```

---

## 🚀 تشغيل السيرفر

### 1. ثبّت المكتبات
```bash
pip install -r requirements.txt
```

### 2. ضع موديلك
انسخ ملف الموديل (`model.h5` أو `efficientnet_model.h5`) داخل المجلد:
```
python-api/model.h5
```

### 3. شغّل السيرفر
```bash
python main.py
```
أو:
```bash
uvicorn main:app --reload --port 8000
```

---

## 🔗 الـ Endpoints

| Method | URL | الوصف |
|--------|-----|-------|
| GET | `/` | فحص حالة السيرفر |
| GET | `/health` | هل الموديل محمّل؟ |
| POST | `/predict` | ارفع صورة واحصل على النتيجة |

---

## 🧪 اختبار من المتصفح

بعد التشغيل افتح: **http://localhost:8000/docs**

ستجد واجهة Swagger تقدر تختبر من خلالها مباشرة!

---

## 📤 مثال على الرد

```json
{
  "riskLevel": "High",
  "probability": 87.3,
  "explanation": "AI analysis detected Diabetic Retinopathy markers...",
  "heatmapBase64": "data:image/png;base64,..."
}
```

---

## ⚙️ تغيير اسم الموديل

في `main.py` السطر 32:
```python
MODEL_PATH = os.getenv("MODEL_PATH", "model.h5")
#                                     ↑ غيّر هذا
```

---

## 🌐 ربطه بالـ Frontend

في `scans.ts` (Node.js backend)، غيّر السطر الذي يستدعي `simulateAI`:
```ts
// بدل simulateAI(buffer):
const pyRes = await fetch("http://localhost:8000/predict", {
  method: "POST",
  body: formData,
});
const aiResult = await pyRes.json();
```
