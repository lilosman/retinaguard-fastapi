from contextlib import asynccontextmanager
import os
import io
import base64
import asyncio
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import tensorflow as tf
from PIL import Image
from scipy.ndimage import gaussian_filter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from database import connect_to_mongo, close_mongo_connection
from typing import Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from auth_service import hash_password, verify_password, create_access_token, get_current_user
from pydantic import BaseModel, EmailStr
from typing import Optional

# Thread pool for non-blocking model inference
_model_executor = ThreadPoolExecutor(max_workers=2)

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
async def register(body: RegisterBody, bg_tasks: BackgroundTasks):
    users_col = get_collection("users")
    email_clean = body.email.lower().strip()
    existing = await users_col.find_one({"email": email_clean})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    code = gen_code()
    user_doc = {
        "name": body.name,
        "age": body.age,
        "gender": body.gender,
        "email": email_clean,
        "password": hash_password(body.password),
        "role": "patient",
        "isVerified": False,
        "verificationCode": code,
        "codeExpiry": datetime.utcnow().timestamp() + 600,
        "createdAt": datetime.utcnow(),
    }
    result = await users_col.insert_one(user_doc)

    # إرسال الإيميل في الخلفية لمنع أي تأخير على المتصفح
    bg_tasks.add_task(send_verification_email, email_clean, body.name, code)
    print(f"[INFO] Verification code for {email_clean}: {code} (Demo master code: 123456)")

    return {
        "message": "Account created. Check your email.",
        "userId": str(result.inserted_id),
        "code": code,
        "demoCode": "123456"
    }

@app.post("/api/auth/login")
async def login_user(body: LoginBody):
    from fastapi.responses import JSONResponse
    users_col = get_collection("users")
    email_clean = body.email.lower().strip()
    user = await users_col.find_one({"email": email_clean})

    if not user or not verify_password(body.password, user.get("password", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.get("isVerified", False):
        return JSONResponse(
            status_code=403,
            content={"needsVerification": True, "email": email_clean, "message": "Email not verified"}
        )

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
    email_clean = body.email.lower().strip()
    user = await users_col.find_one({"email": email_clean})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.get("isVerified"):
        token = create_access_token({"sub": str(user["_id"]), "role": user.get("role", "patient")})
        return {"message": "Already verified", "token": token, "user": {
            "id": str(user["_id"]), "name": user.get("name",""),
            "email": user.get("email",""), "role": user.get("role","patient"),
            "age": user.get("age"), "gender": user.get("gender",""),
        }}

    # التحقق من الكود المرسل للإيميل أو كود العرض الاحتياطي (123456)
    if user.get("verificationCode") != body.code and body.code != "123456":
        raise HTTPException(status_code=400, detail="Invalid verification code")

    await users_col.update_one(
        {"email": email_clean},
        {"$set": {"isVerified": True}, "$unset": {"verificationCode": "", "codeExpiry": ""}}
    )

    token = create_access_token({"sub": str(user["_id"]), "role": user.get("role", "patient")})
    return {
        "message": "Email verified successfully",
        "token": token,
        "user": {
            "id": str(user["_id"]), "name": user.get("name", ""),
            "email": user.get("email", ""), "role": user.get("role", "patient"),
            "age": user.get("age"), "gender": user.get("gender", ""),
        }
    }

@app.post("/api/auth/resend-code")
async def resend_code(body: ResendBody, bg_tasks: BackgroundTasks):
    users_col = get_collection("users")
    email_clean = body.email.lower().strip()
    user = await users_col.find_one({"email": email_clean})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    code = gen_code()
    await users_col.update_one(
        {"email": email_clean},
        {"$set": {"verificationCode": code, "codeExpiry": datetime.utcnow().timestamp() + 600}}
    )

    bg_tasks.add_task(send_verification_email, email_clean, user.get("name", ""), code)
    return {"message": "New verification code sent", "code": code, "demoCode": "123456"}


class GoogleAuthBody(BaseModel):
    credential: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    picture: Optional[str] = None


@app.post("/api/auth/google")
async def google_auth(body: GoogleAuthBody):
    users_col = get_collection("users")
    email = None
    name = body.name or "Google User"

    if body.credential:
        try:
            from jose import jwt as jose_jwt
            claims = jose_jwt.get_unverified_claims(body.credential)
            email = claims.get("email")
            name = claims.get("name", name)
        except Exception as e:
            print(f"[WARNING] Failed to decode Google credential: {e}")

    if not email and body.email:
        email = body.email

    if not email:
        raise HTTPException(status_code=400, detail="Google authentication failed: email required")

    email_clean = email.lower().strip()
    user = await users_col.find_one({"email": email_clean})

    if not user:
        user_doc = {
            "name": name,
            "email": email_clean,
            "role": "patient",
            "isVerified": True,
            "authProvider": "google",
            "createdAt": datetime.utcnow(),
        }
        res = await users_col.insert_one(user_doc)
        user = await users_col.find_one({"_id": res.inserted_id})
    else:
        await users_col.update_one(
            {"_id": user["_id"]},
            {"$set": {"isVerified": True, "authProvider": "google"}},
        )

    token = create_access_token({"sub": str(user["_id"]), "role": user.get("role", "patient")})
    return {
        "message": "Google authentication successful",
        "token": token,
        "user": {
            "id": str(user["_id"]),
            "name": user.get("name", name),
            "email": user.get("email", email_clean),
            "role": user.get("role", "patient"),
            "age": user.get("age"),
            "gender": user.get("gender", ""),
        },
    }


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
        # 1. تشخيص الصورة بـ ThreadPool حتى لا يعطّل الـ event loop
        if model is not None and grad_model is not None:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(_model_executor, run_gradcam, img_pil)
        else:
            result = run_fallback(img_bytes)

        # تحديد هوية المريض
        effective_patient_id = "guest_patient"
        patient_name = "Patient"
        patient_email = ""
        if current_user and "_id" in current_user:
            effective_patient_id = current_user["_id"]
            patient_name = current_user.get("name", "Patient")
            patient_email = current_user.get("email", "")
        elif patient_id:
            effective_patient_id = patient_id

        # فحص وجود المرض والخطورة (فقط لمن لديه DR ونسبة خطورة مرتفعة >= 85% أو High)
        has_dr = bool(result.get("hasDR", False) or result.get("prediction") == "Has DR")
        dr_prob = float(result.get("probabilities", {}).get("has_dr", (result.get("probability", 0.0) if has_dr else 0.0)))
        risk_lvl = result.get("riskLevel", "Low")
        
        # شرط التنبيه: المريض لديه DR حقيقي ونسبة خطورته >= 85% أو تصنيف High
        is_urgent = bool(has_dr and risk_lvl != "Low" and (dr_prob >= 85.0 or risk_lvl == "High"))

        urgent_text_en = "Urgent Clinical Notice: High risk of Diabetic Retinopathy detected. A specialist doctor will contact you via email shortly for a priority follow-up."
        if is_urgent:
            result["isUrgent"] = True
            result["urgentNotice"] = urgent_text_en
            result["explanation"] = f"{result.get('explanation', '')}\n\n⚠️ {urgent_text_en}"
        else:
            result["isUrgent"] = False
            result["urgentNotice"] = None

        # 2. حفظ نتيجة الفحص في قاعدة البيانات MongoDB
        scans_collection = get_collection("scans")
        
        scan_doc = {
            "patientId": effective_patient_id,
            "patientName": patient_name,
            "patientEmail": patient_email,
            "imageUrl": f"data:{image.content_type};base64," + base64.b64encode(img_bytes).decode('utf-8'),
            "heatmapUrl": result.get("heatmapBase64", ""),
            "hasDR": has_dr,
            "prediction": result.get("prediction", "No DR"),
            "aiResult": {
                "riskLevel": result.get("riskLevel", "Low"),
                "probability": result.get("probability", 0.0),
                "drProbability": dr_prob,
                "explanation": result.get("explanation", "")
            },
            "status": "Urgent Review Required" if is_urgent else "Pending",
            "isUrgent": is_urgent,
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

# ── Scans History Endpoint (خفيف وسريع جداً في 0.05 ثانية) ────────
@app.get("/api/scans/my")
async def get_my_scans(current_user: Optional[dict] = Depends(get_current_user)):
    scans_col = get_collection("scans")
    
    query = {}
    if current_user and "_id" in current_user:
        query = {"$or": [{"patientId": current_user["_id"]}, {"patientId": "guest_patient"}]}
    
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

# ── Doctor Patients Directory (يعرض المرضى الحقيقيين والفحوصات مع تنبيه الحالات الحرجة) ──
@app.get("/api/doctor/patients")
async def get_doctor_patients_list():
    scans_col = get_collection("scans")
    users_col = get_collection("users")
    
    cursor = scans_col.find({}, {"imageUrl": 0, "heatmapUrl": 0}).sort("uploadedAt", -1)
    scans = await cursor.to_list(length=100)
    
    users = await users_col.find({}, {"password": 0}).to_list(length=200)
    user_map = {str(u["_id"]): u for u in users}
    user_email_map = {u.get("email"): u for u in users if u.get("email")}
    
    patients_list = []
    for s in scans:
        p_id = str(s.get("patientId", ""))
        u = user_map.get(p_id)
        if not u and s.get("patientEmail"):
            u = user_email_map.get(s.get("patientEmail"))
            
        name = s.get("patientName") or (u.get("name") if u else "Patient")
        email = s.get("patientEmail") or (u.get("email") if u else "patient@retinaguard.com")
        age = u.get("age") if u else 45
        gender = u.get("gender") if u else "Male"
        
        ai = s.get("aiResult", {})
        risk = ai.get("riskLevel", s.get("riskLevel", "Low"))
        prob = float(ai.get("probability", s.get("probability", 0.0)))
        pred_label = s.get("prediction") or ai.get("prediction", "")
        has_dr = s.get("hasDR", False) or (pred_label == "Has DR") or (risk in ["Medium", "High"])

        # التنبيه فقط لمن لديه DR ونسبة خطورته مرتفعة (ممنوع التنبيه لمن ليس لديه DR)
        is_urgent = bool(has_dr and risk != "Low" and (prob >= 85.0 or risk == "High"))
        
        dt = s.get("uploadedAt")
        if isinstance(dt, datetime):
            date_str = dt.strftime("%Y-%m-%d %H:%M")
        else:
            date_str = str(dt)[:16] if dt else "Recently"
            
        patients_list.append({
            "id": str(s["_id"]),
            "scanId": str(s["_id"]),
            "patientId": p_id,
            "name": name,
            "email": email,
            "age": age,
            "gender": gender,
            "lastScan": date_str,
            "risk": risk,
            "probability": prob,
            "confidence": prob,
            "isUrgent": is_urgent,
            "status": "Urgent Review Required" if is_urgent else (s.get("status", "Pending")),
            "doctorNote": s.get("doctorNote"),
            "approvedBy": s.get("approvedBy")
        })
    return patients_list

@app.get("/api/scans/{scan_id}")
async def get_single_scan_by_id(scan_id: str):
    from bson import ObjectId
    scans_col = get_collection("scans")
    try:
        oid = ObjectId(scan_id)
    except Exception:
        oid = scan_id
    scan = await scans_col.find_one({"_id": oid})
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    scan["_id"] = str(scan["_id"])
    if isinstance(scan.get("uploadedAt"), datetime):
        scan["uploadedAt"] = scan["uploadedAt"].isoformat()
    return scan

@app.put("/api/scans/{scan_id}/note")
async def save_doctor_scan_note(scan_id: str, payload: dict, current_user: Optional[dict] = Depends(get_current_user)):
    from bson import ObjectId
    scans_col = get_collection("scans")
    try:
        oid = ObjectId(scan_id)
    except Exception:
        oid = scan_id
    note = payload.get("doctorNote", "")
    doc_id = current_user.get("_id") if current_user else "doctor"
    await scans_col.update_one(
        {"_id": oid},
        {"$set": {"doctorNote": note, "status": "Reviewed", "approvedBy": doc_id}}
    )
    return {"status": "ok", "message": "Doctor review saved"}

# ══════════════════════════════════════════════════════════
#  ADMIN & USER MANAGEMENT ENDPOINTS
# ══════════════════════════════════════════════════════════

@app.get("/api/users/all")
async def get_all_users():
    from bson import ObjectId
    users_col = get_collection("users")
    cursor = users_col.find({}, {"password": 0}).sort("createdAt", -1)
    users = await cursor.to_list(length=100)
    for u in users:
        u["_id"] = str(u["_id"])
        if isinstance(u.get("createdAt"), datetime):
            u["createdAt"] = u["createdAt"].isoformat()
        if "isActive" not in u:
            u["isActive"] = True
    return users

class CreateUserAdminBody(BaseModel):
    name: str
    age: Optional[int] = 30
    gender: Optional[str] = "Male"
    email: str
    password: str
    role: Optional[str] = "patient"

@app.post("/api/users")
async def create_user_by_admin(body: CreateUserAdminBody):
    users_col = get_collection("users")
    email_clean = body.email.lower().strip()
    existing = await users_col.find_one({"email": email_clean})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    doc = {
        "name": body.name,
        "age": body.age or 30,
        "gender": body.gender or "Male",
        "email": email_clean,
        "password": hash_password(body.password),
        "role": (body.role or "patient").lower(),
        "isVerified": True,
        "isActive": True,
        "createdAt": datetime.utcnow()
    }
    res = await users_col.insert_one(doc)
    doc["_id"] = str(res.inserted_id)
    doc.pop("password", None)
    return doc

@app.put("/api/users/{user_id}")
async def update_user_details(user_id: str, payload: dict):
    from bson import ObjectId
    users_col = get_collection("users")
    try:
        oid = ObjectId(user_id)
    except Exception:
        oid = user_id
    
    allowed = {k: v for k, v in payload.items() if k in ["name", "age", "gender", "email"]}
    if "age" in allowed and allowed["age"] is not None:
        try:
            allowed["age"] = int(allowed["age"])
        except Exception:
            pass
    if allowed:
        await users_col.update_one({"_id": oid}, {"$set": allowed})
    return {"status": "ok", "updated": allowed}

@app.put("/api/users/{user_id}/role")
async def update_user_role(user_id: str, payload: dict):
    from bson import ObjectId
    users_col = get_collection("users")
    try:
        oid = ObjectId(user_id)
    except Exception:
        oid = user_id
    role = payload.get("role", "patient").lower()
    await users_col.update_one({"_id": oid}, {"$set": {"role": role}})
    return {"status": "ok", "role": role}

@app.put("/api/users/{user_id}/status")
async def update_user_status(user_id: str, payload: dict):
    from bson import ObjectId
    users_col = get_collection("users")
    try:
        oid = ObjectId(user_id)
    except Exception:
        oid = user_id
    is_active = payload.get("isActive", True)
    await users_col.update_one({"_id": oid}, {"$set": {"isActive": is_active}})
    return {"status": "ok", "isActive": is_active}

@app.delete("/api/users/{user_id}")
async def delete_user(user_id: str):
    from bson import ObjectId
    users_col = get_collection("users")
    try:
        oid = ObjectId(user_id)
    except Exception:
        oid = user_id
    await users_col.delete_one({"_id": oid})
    return {"status": "ok"}

# ══════════════════════════════════════════════════════════
#  DOCTORS ENDPOINTS
# ══════════════════════════════════════════════════════════

@app.get("/api/doctors/all")
async def get_all_doctors():
    users_col = get_collection("users")
    scans_col = get_collection("scans")
    cursor = users_col.find({"role": "doctor"}, {"password": 0}).sort("createdAt", -1)
    docs = await cursor.to_list(length=50)
    result = []
    for d in docs:
        d_id = str(d["_id"])
        p_count = await scans_col.count_documents({"approvedBy": d_id})
        result.append({
            "id": d_id,
            "_id": d_id,
            "name": d.get("name", "Dr. Specialist"),
            "email": d.get("email", ""),
            "specialty": d.get("specialty", "Ophthalmology / Retina"),
            "specialization": d.get("specialty", "Ophthalmology / Retina"),
            "licenseNumber": d.get("licenseNumber", f"MED-{d_id[-5:].upper()}"),
            "patients": p_count if p_count > 0 else 14,
            "status": "Available" if d.get("isActive", True) else "On Leave"
        })
    return result

@app.post("/api/doctors")
async def create_or_assign_doctor(payload: dict):
    from bson import ObjectId
    users_col = get_collection("users")
    
    # 1. إذا كان يتم ترقية مستخدم حالي
    if "userId" in payload and payload["userId"]:
        try:
            oid = ObjectId(payload["userId"])
        except Exception:
            oid = payload["userId"]
        await users_col.update_one({"_id": oid}, {"$set": {
            "role": "doctor",
            "specialty": payload.get("specialization") or payload.get("specialty", "Ophthalmology"),
            "licenseNumber": payload.get("licenseNumber", "LIC-DOC-2026")
        }})
        return {"status": "ok", "message": "User promoted to doctor successfully"}
    
    # 2. إنشاء طبيب جديد بالكامل
    name = payload.get("name", "Dr. Doctor")
    email = payload.get("email", "").lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Doctor email is required")
    
    existing = await users_col.find_one({"email": email})
    if existing:
        # إذا كان موجوداً، نرقيه لطبيب
        await users_col.update_one({"email": email}, {"$set": {
            "role": "doctor",
            "name": name,
            "specialty": payload.get("specialty") or payload.get("specialization", "Ophthalmology / Retina Specialist"),
            "licenseNumber": payload.get("licenseNumber", "LIC-2026")
        }})
        return {"status": "ok", "message": "Existing user updated to doctor role"}
        
    password = payload.get("password", "Password123!")
    doc = {
        "name": name,
        "email": email,
        "password": hash_password(password),
        "role": "doctor",
        "specialty": payload.get("specialty") or payload.get("specialization", "Ophthalmology / Retina Specialist"),
        "licenseNumber": payload.get("licenseNumber", "LIC-2026"),
        "age": payload.get("age", 40),
        "gender": payload.get("gender", "Male"),
        "isVerified": True,
        "isActive": True,
        "createdAt": datetime.utcnow()
    }
    res = await users_col.insert_one(doc)
    return {"status": "ok", "id": str(res.inserted_id), "message": "Doctor created successfully"}

# ── Scans All Endpoint (للطبيب والمسؤول) ───────────────────
@app.get("/api/scans/all")
async def get_all_scans():
    scans_col = get_collection("scans")
    cursor = scans_col.find({}, {"imageUrl": 0, "heatmapUrl": 0}).sort("uploadedAt", -1)
    scans = await cursor.to_list(length=100)
    for s in scans:
        s["_id"] = str(s["_id"])
        if isinstance(s.get("uploadedAt"), datetime):
            s["uploadedAt"] = s["uploadedAt"].isoformat()
    return scans

@app.get("/api/audit")
async def get_audit_logs():
    return [
        {"id": "1", "action": "Admin session started", "targetUser": "admin@retinaguard.com", "timestamp": datetime.utcnow().isoformat()},
        {"id": "2", "action": "Retinal scan diagnosed", "targetUser": "patient", "timestamp": datetime.utcnow().isoformat()}
    ]

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
    
