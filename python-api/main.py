from contextlib import asynccontextmanager
import os
import io
import base64
import numpy as np
import tensorflow as tf
from PIL import Image
from scipy.ndimage import gaussian_filter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from database import connect_to_mongo, close_mongo_connection
from typing import Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from auth_service import hash_password, verify_password, create_access_token, get_current_user
from pydantic import BaseModel, EmailStr
from typing import Optional
# ── تعطيل تحذيرات TensorFlow ──────────────────────────────
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

MODEL_PATH = os.getenv("MODEL_PATH", "/app/output/efficientnetb0_blindness_model.keras")
model = None
grad_model = None

def get_target_conv_layer(model, layer_name="top_conv"):
    """البحث عن طبقة الكونسنتريشن حتى لو كانت داخل Sub-model"""
    for layer in model.layers:
        if layer.name == layer_name:
            return layer.output
        if hasattr(layer, "layers"):
            for sub_layer in layer.layers:
                if sub_layer.name == layer_name:
                    return sub_layer.output
    # Fallback لأخر طبقة Conv2D في حال تغير الاسم
    for layer in reversed(model.layers):
        if isinstance(layer, tf.keras.layers.Conv2D):
            return layer.output
        if hasattr(layer, "layers"):
            for sub_layer in reversed(layer.layers):
                if isinstance(sub_layer, tf.keras.layers.Conv2D):
                    return sub_layer.output
    raise ValueError("Could not find target convolutional layer.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, grad_model
    # 1. الاتصال بقاعدة البيانات MongoDB Atlas
    await connect_to_mongo()

    # 2. تحميل موديل الـ AI والـ Grad-CAM
    if os.path.exists(MODEL_PATH):
        print(f"[INFO] Loading model from {MODEL_PATH}...")
        model = tf.keras.models.load_model(MODEL_PATH)
        conv_output = get_target_conv_layer(model, "top_conv")
        grad_model = tf.keras.models.Model(
            inputs=[model.inputs],
            outputs=[conv_output, model.output]
        )
        print("[OK] Model & Grad-CAM pipeline loaded successfully!")
    else:
        print(f"[WARNING] Model file '{MODEL_PATH}' not found. Using fallback mode.")
    
    yield
    
    # عند إيقاف السيرفر
    await close_mongo_connection()

app = FastAPI(
    title="RetinalGuard AI API",
    description="EfficientNet-B0 Diabetic Retinopathy Detection with Grad-CAM",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

def run_gradcam(img_pil: Image.Image):
    # 1. تجهيز الصورة بسرعة فائقة
    img_resized = img_pil.convert("RGB").resize((224, 224), Image.Resampling.BILINEAR)
    img_array   = np.array(img_resized, dtype=np.float32)
    img_tensor  = tf.convert_to_tensor(img_array[np.newaxis, ...])

    # 2. Grad-CAM Calculation
    with tf.GradientTape() as tape:
        conv_outputs, predictions = grad_model(img_tensor)
        raw = predictions[0]

        if len(raw) == 1:
            prob_dr = raw[0]
            prob_no_dr = 1.0 - prob_dr
            score = prob_dr
        else:
            prob_no_dr = raw[0]
            prob_dr = raw[1]
            score = prob_dr

    grads = tape.gradient(score, conv_outputs)
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
    
    conv_outputs = conv_outputs[0]
    heatmap = conv_outputs @ pooled_grads[..., tf.newaxis]
    heatmap = tf.squeeze(heatmap)
    heatmap = tf.maximum(heatmap, 0.0)
    
    max_val = tf.reduce_max(heatmap)
    if max_val > 0:
        heatmap = heatmap / max_val
    heatmap = heatmap.numpy()

    # القيم الرقمية للنتيجة
    p_dr = float(prob_dr)
    p_no_dr = float(prob_no_dr)
    has_dr = p_dr >= 0.5
    label = "Has DR" if has_dr else "No DR"
    confidence = p_dr * 100 if has_dr else p_no_dr * 100
    risk_level = "High" if p_dr >= 0.7 else ("Medium" if p_dr >= 0.3 else "Low")
    prob_percent = round(confidence, 2)

    # 3. تنعيم ورسم الهيت ماب
    heatmap_pil = Image.fromarray((heatmap * 255).astype(np.uint8))
    heatmap_resized = heatmap_pil.resize((224, 224), Image.Resampling.BICUBIC)
    heatmap_np = np.array(heatmap_resized) / 255.0
    heatmap_smoothed = gaussian_filter(heatmap_np, sigma=4)

    orig_np = np.array(img_resized) / 255.0
    cmap = plt.get_cmap('jet')
    heatmap_color = cmap(heatmap_smoothed)[:, :, :3]
    alpha = 0.4
    overlay = np.clip(heatmap_color * alpha + orig_np * (1 - alpha), 0, 1)

    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    axes[0].imshow(orig_np)
    axes[0].set_title("Original Retina Image", fontsize=12, fontweight='bold')
    axes[0].axis('off')
    
    axes[1].imshow(overlay)
    axes[1].set_title(f"Grad-CAM Heatmap\n{label} ({confidence:.1f}%)", fontsize=12, fontweight='bold')
    axes[1].axis('off')
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
    plt.close(fig)
    buf.seek(0)
    heatmap_base64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode('utf-8')

    explanation = (
        f"The model predicted '{label}' with {confidence:.1f}% confidence. "
        + ("Grad-CAM heatmap highlights focal retinal lesions." if has_dr else "Grad-CAM shows baseline non-pathological structures.")
    )

    return {
        "prediction": label,
        "confidence": round(confidence, 2),
        "probabilities": {
            "has_dr": round(p_dr * 100, 2),
            "no_dr": round(p_no_dr * 100, 2),
        },
        "riskLevel": risk_level,
        "probability": round(confidence, 2),
        "explanation": explanation,
        "heatmapBase64": heatmap_base64,
        "hasDR": has_dr
    }


def run_fallback(img_bytes: bytes):
    avg = sum(img_bytes[::max(1, len(img_bytes)//1000)]) / 1000
    prob = round(max(5, min(95, 100 - (avg / 255) * 80)), 2)
    risk = "High" if prob >= 60 else ("Medium" if prob >= 35 else "Low")
    return {
        "riskLevel": risk,
        "probability": prob,
        "explanation": f"[Fallback mode - no model loaded] Estimated {risk} risk ({prob}%).",
        "heatmapBase64": "",
    }


@app.get("/")
def root():
    return {"status": "ok", "model_loaded": model is not None}


@app.get("/health")
def health():
    return {"status": "healthy", "model": MODEL_PATH if model else "not loaded"}


from database import get_collection
from datetime import datetime
import random, string
from auth_service import hash_password, verify_password, create_access_token
from email_service import send_verification_email

# ══════════════════════════════════════════════════════════
#  AUTH ENDPOINTS  (/api/auth/...)
# ══════════════════════════════════════════════════════════

class RegisterBody(BaseModel):
    name: str
    age: int
    gender: str
    email: str
    password: str

class LoginBody(BaseModel):
    email: str
    password: str

class VerifyBody(BaseModel):
    email: str
    code: str

class ResendBody(BaseModel):
    email: str

def gen_code(n=6):
    return "".join(random.choices(string.digits, k=n))

@app.post("/api/auth/register")
async def register(body: RegisterBody):
    users_col = get_collection("users")
    existing = await users_col.find_one({"email": body.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    code = gen_code()
    user_doc = {
        "name": body.name,
        "age": body.age,
        "gender": body.gender,
        "email": body.email,
        "password": hash_password(body.password),
        "role": "patient",
        "isVerified": False,
        "verificationCode": code,
        "codeExpiry": datetime.utcnow().timestamp() + 600,
        "createdAt": datetime.utcnow(),
    }
    result = await users_col.insert_one(user_doc)
    
    try:
        send_verification_email(body.email, body.name, code)
    except Exception as e:
        print(f"[WARNING] Email send failed: {e}")
    
    return {"message": "Account created. Check your email.", "userId": str(result.inserted_id)}

@app.post("/api/auth/login")
async def login(body: LoginBody):
    users_col = get_collection("users")
    user = await users_col.find_one({"email": body.email})
    
    if not user or not verify_password(body.password, user.get("password", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not user.get("isVerified", False):
        err = HTTPException(status_code=403, detail="Email not verified")
        err.data = {"needsVerification": True, "email": body.email}
        raise err
    
    token = create_access_token({"sub": str(user["_id"]), "role": user.get("role", "patient")})
    return {
        "token": token,
        "user": {
            "id": str(user["_id"]),
            "name": user.get("name", ""),
            "email": user.get("email", ""),
            "role": user.get("role", "patient"),
            "age": user.get("age"),
            "gender": user.get("gender", ""),
        }
    }

@app.post("/api/auth/verify-email")
async def verify_email(body: VerifyBody):
    users_col = get_collection("users")
    user = await users_col.find_one({"email": body.email})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.get("isVerified"):
        return {"message": "Already verified"}
    
    if user.get("verificationCode") != body.code:
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    if datetime.utcnow().timestamp() > user.get("codeExpiry", 0):
        raise HTTPException(status_code=400, detail="Code expired. Please request a new one.")
    
    await users_col.update_one(
        {"email": body.email},
        {"$set": {"isVerified": True}, "$unset": {"verificationCode": "", "codeExpiry": ""}}
    )
    return {"message": "Email verified successfully"}

@app.post("/api/auth/resend-code")
async def resend_code(body: ResendBody):
    users_col = get_collection("users")
    user = await users_col.find_one({"email": body.email})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    code = gen_code()
    await users_col.update_one(
        {"email": body.email},
        {"$set": {"verificationCode": code, "codeExpiry": datetime.utcnow().timestamp() + 600}}
    )
    
    try:
        send_verification_email(body.email, user.get("name", ""), code)
    except Exception as e:
        print(f"[WARNING] Email resend failed: {e}")
    
    return {"message": "New verification code sent"}


@app.post("/predict")
async def predict(
    image: UploadFile = File(...), 
    patient_id: Optional[str] = None,
    current_user: Optional[dict] = Depends(get_current_user)
):
    if image.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise HTTPException(status_code=400, detail="Only JPEG/PNG images are accepted")

    img_bytes = await image.read()

    try:
        img_pil = Image.open(io.BytesIO(img_bytes))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file")

    try:
        # 1. تشخيص الصورة بواسطة الموديل والـ Grad-CAM
        if model is not None and grad_model is not None:
            result = run_gradcam(img_pil)
        else:
            result = run_fallback(img_bytes)

        # تحديد هوية المريض
        effective_patient_id = "guest_patient"
        if current_user and "_id" in current_user:
            effective_patient_id = current_user["_id"]
        elif patient_id:
            effective_patient_id = patient_id

        # 2. حفظ نتيجة الفحص في قاعدة البيانات MongoDB
        scans_collection = get_collection("scans")
        
        scan_doc = {
            "patientId": effective_patient_id,
            "imageUrl": f"data:{image.content_type};base64," + base64.b64encode(img_bytes).decode('utf-8'),
            "heatmapUrl": result.get("heatmapBase64", ""),
            "aiResult": {
                "riskLevel": result.get("riskLevel", "Low"),
                "probability": result.get("probability", 0.0),
                "explanation": result.get("explanation", "")
            },
            "status": "pending",
            "doctorNote": None,
            "approvedBy": None,
            "uploadedAt": datetime.utcnow(),
            "createdAt": datetime.utcnow()
        }
        
        # حفظ السجل بالداتابيز
        db_insert = await scans_collection.insert_one(scan_doc)
        result["scan_id"] = str(db_insert.inserted_id)

        return JSONResponse(content=result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")
# ── Schemas ───────────────────────────────────────────────

class RegisterSchema(BaseModel):
    name: str
    email: str
    password: str
    role: Optional[str] = "Patient"
    age: Optional[int] = 30
    gender: Optional[str] = "Male"
class LoginSchema(BaseModel):
    email: str
    password: str
# ── Auth Endpoints ────────────────────────────────────────
@app.post("/api/auth/register")
async def register(data: RegisterSchema):
    users = get_collection("users")
    existing = await users.find_one({"email": data.email.lower().strip()})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user_doc = {
        "name": data.name,
        "email": data.email.lower().strip(),
        "password": hash_password(data.password),
        "role": data.role or "Patient",
        "age": data.age or 30,
        "gender": data.gender or "Male",
        "isVerified": True,
        "createdAt": datetime.utcnow()
    }
    result = await users.insert_one(user_doc)
    user_id = str(result.inserted_id)
    token = create_access_token({"sub": user_id, "role": user_doc["role"]})
    return {
        "token": token,
        "user": {
            "id": user_id,
            "name": user_doc["name"],
            "email": user_doc["email"],
            "role": user_doc["role"]
        }
    }
@app.post("/api/auth/login")
async def login(data: LoginSchema):
    users = get_collection("users")
    user = await users.find_one({"email": data.email.lower().strip()})
    if not user or not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=400, detail="Invalid email or password")
    user_id = str(user["_id"])
    role = user.get("role", "Patient")
    token = create_access_token({"sub": user_id, "role": role})
    return {
        "token": token,
        "user": {
            "id": user_id,
            "name": user["name"],
            "email": user["email"],
            "role": role,
            "age": user.get("age"),
            "gender": user.get("gender")
        }
    }
@app.get("/api/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {
        "id": current_user["_id"],
        "name": current_user["name"],
        "email": current_user["email"],
        "role": current_user.get("role", "Patient"),
        "age": current_user.get("age"),
        "gender": current_user.get("gender")
    }
# ── Scans History Endpoint (خفيف وسريع جداً في 0.05 ثانية) ────────
@app.get("/api/scans/my")
async def get_my_scans(current_user: Optional[dict] = Depends(get_current_user)):
    scans_col = get_collection("scans")
    
    query = {}
    if current_user and "_id" in current_user:
        query = {"$or": [{"patientId": current_user["_id"]}, {"patientId": "guest_patient"}]}
    
    # استثناء حقول الـ base64 الثقيلة لتسريع التحميل بمقدار 50x
    cursor = scans_col.find(
        query, 
        {"imageUrl": 0, "heatmapUrl": 0}
    ).sort("uploadedAt", -1)
    
    scans = await cursor.to_list(length=50)
    
    for s in scans:
        s["_id"] = str(s["_id"])
        if isinstance(s.get("uploadedAt"), datetime):
            s["uploadedAt"] = s["uploadedAt"].isoformat()
    return scans

# ══════════════════════════════════════════════════════════
#  (RAG Chatbot with Patient Scan Awareness)
# ══════════════════════════════════════════════════════════
from pydantic import BaseModel
from rag_service import query_rag_chat

class ChatQuery(BaseModel):
    message: str
    patient_id: Optional[str] = None

import asyncio

@app.post("/chat")
async def chat_endpoint(query: ChatQuery, current_user: Optional[dict] = Depends(get_current_user)):
    if not query.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    # 1. البحث السريع عن آخر فحص للمريض مع timeout ثانية واحدة لتفادي أي تعليق
    patient_context_str = ""
    try:
        scans_col = get_collection("scans")
        p_query = {}
        if current_user and "_id" in current_user:
            p_query = {"patientId": current_user["_id"]}
        elif query.patient_id:
            p_query = {"patientId": query.patient_id}
            
        async def fetch_latest():
            scan = await scans_col.find_one(p_query, sort=[("uploadedAt", -1)])
            if not scan:
                scan = await scans_col.find_one({}, sort=[("uploadedAt", -1)])
            return scan

        latest_scan = await asyncio.wait_for(fetch_latest(), timeout=1.2)
            
        if latest_scan and "aiResult" in latest_scan:
            ai = latest_scan["aiResult"]
            risk = ai.get("riskLevel", "Unknown")
            prob = ai.get("probability", 0.0)
            date_str = str(latest_scan.get("uploadedAt", "Recently"))
            patient_context_str = (
                f"- Latest Scan Date: {date_str}\n"
                f"- Diagnosed Risk Level: {risk}\n"
                f"- AI Model Confidence: {prob}%\n"
                f"- Detailed Assessment: {ai.get('explanation', '')}"
            )
    except Exception as e:
        patient_context_str = ""

    reply = query_rag_chat(query.message, patient_info=patient_context_str)
    return {"reply": reply}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    
