import os
import requests
from config import settings

# 1. تحميل مقتطفات المراجع الطبية المرفقة في الذاكرة للبحث الفوري (في 0.001 ثانية)
MEDICAL_PAPERS_CONTEXT = """
DIABETIC RETINOPATHY CLINICAL GUIDELINES & RESEARCH FINDINGS:
1. Classification & Grading:
   - No DR: No abnormalities visible on fundus examination.
   - Mild NPDR: Microaneurysms only. Annual dilated eye exam recommended.
   - Moderate NPDR: Microaneurysms, dot/blot hemorrhages, hard exudates, cotton wool spots. Follow up every 3 to 6 months.
   - Severe NPDR: 4-2-1 rule (>20 intraretinal hemorrhages in each of 4 quadrants, venous beading in 2+ quadrants, IRMA in 1+ quadrant). Urgent ophthalmology referral within 1 month.
   - Proliferative DR (PDR): Neovascularization of disc (NVD) or elsewhere (NVE), preretinal/vitreous hemorrhage, fibrous proliferation. Urgent Pan-retinal Photocoagulation (PRP) or Anti-VEGF therapy required.

2. Diabetic Macular Edema (DME):
   - Retinal thickening or hard exudates involving or threatening the fovea.
   - First-line treatment: Intravitreal Anti-VEGF agents (Aflibercept, Ranibizumab) or Triamcinolone acetonide steroids and focal/grid laser photocoagulation.

3. Systemic Risk Factor Management:
   - Strict glycemic control (target HbA1c <= 7.0%) slows DR progression significantly.
   - Blood pressure control (<130/80 mmHg) and lipid-lowering therapy reduce retinal microvascular leakage.
   - Cessation of smoking and regular cardiovascular exercise (>=150 min/week).

4. Early Warning Symptoms for Urgent Care:
   - Sudden onset of dark floating spots (floaters), flashes of light, blurred or distorted vision, or dark curtains/shadows in visual field.
"""

# 2. Groq API Call
def ask_groq(system_prompt: str, user_prompt: str) -> str:
    api_key = settings.GROQ_API_KEY
    if not api_key:
        return "GROQ_API_KEY is not configured in settings."

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key.strip()}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-oss-20b",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.2,
                "max_tokens": 512
            },
            timeout=15
        )
        response.encoding = "utf-8"
        data = response.json()
        
        if "error" in data:
            return f"AI Service Error: {data['error'].get('message', str(data['error']))}"

        if "choices" in data and len(data["choices"]) > 0:
            return data['choices'][0]['message']['content'].strip()
        else:
            return f"Unexpected AI response format."

    except Exception as e:
        return f"Error connecting to AI service: {str(e)}"

# 3. RAG Query with Live Patient Examination Awareness
def query_rag_chat(user_question: str, patient_info: str = "") -> str:
    system_prompt = (
        "You are RetinaGuard AI, an expert, compassionate clinical assistant for Diabetic Retinopathy.\n"
        "Instructions:\n"
        "1. Provide clear, well-structured, professional answers using concise bullet points and bold headers.\n"
        "2. If Patient Examination Record is provided, ALWAYS tailor your explanation and guidance directly to their specific diagnosis and risk level.\n"
        "3. Answer based on the clinical guidelines and reference research context provided.\n"
        "4. DO NOT generate complex ASCII tables with pipes (|)."
    )

    user_prompt = (
        f"### Patient Examination Record:\n{patient_info if patient_info else 'No recent scan recorded.'}\n\n"
        f"### Medical Reference Context (From Guidelines & Research Papers):\n{MEDICAL_PAPERS_CONTEXT}\n\n"
        f"### Patient Question:\n{user_question}"
    )

    return ask_groq(system_prompt, user_prompt)