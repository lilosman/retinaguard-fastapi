import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import settings

def send_verification_email(to_email: str, name: str, code: str) -> bool:
    email_user = settings.EMAIL_USER
    email_pass = settings.EMAIL_PASS

    # إذا ما في إيميل مخصص، يستمر بدون خطأ
    if not email_user or not email_pass:
        print(f"⚠️ EMAIL_USER/EMAIL_PASS not configured. Verification code for {to_email} is: {code}")
        return True

    # قالب الـ HTML الأنيق المطابق تماماً
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Verify your RetinaGuard AI account</title>
</head>
<body style="margin:0;padding:0;background:#f4f7fb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f7fb;padding:40px 0;">
    <tr><td align="center">
      <table width="520" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 2px 24px rgba(0,0,0,0.07);">
        <tr>
          <td style="background:linear-gradient(135deg,#1a6cf6 0%,#0ea5e9 100%);padding:36px 40px;text-align:center;">
            <p style="margin:0;font-size:28px;font-weight:700;color:#fff;letter-spacing:-0.5px;">RetinaGuard <span style="color:#bfdbfe;">AI</span></p>
            <p style="margin:8px 0 0;font-size:14px;color:rgba(255,255,255,0.75);">Clinical-grade retinal diagnostics</p>
          </td>
        </tr>
        <tr>
          <td style="padding:40px;">
            <p style="margin:0 0 8px;font-size:22px;font-weight:600;color:#111827;">Hi {name},</p>
            <p style="margin:0 0 32px;font-size:15px;color:#6b7280;line-height:1.6;">Thank you for registering with RetinaGuard AI. To complete your account setup, please enter the verification code below.</p>

            <div style="background:#f0f7ff;border:1.5px solid #bfdbfe;border-radius:12px;padding:28px;text-align:center;margin-bottom:32px;">
              <p style="margin:0 0 8px;font-size:13px;font-weight:500;color:#6b7280;text-transform:uppercase;letter-spacing:1px;">Your verification code</p>
              <p style="margin:0;font-size:42px;font-weight:700;color:#1a6cf6;letter-spacing:10px;">{code}</p>
              <p style="margin:12px 0 0;font-size:13px;color:#9ca3af;">This code expires in 10 minutes.</p>
            </div>

            <p style="margin:0;font-size:13px;color:#9ca3af;line-height:1.6;">If you did not create an account, you can safely ignore this email. For security, do not share this code with anyone.</p>
          </td>
        </tr>
        <tr>
          <td style="padding:20px 40px;border-top:1px solid #f3f4f6;text-align:center;">
            <p style="margin:0;font-size:12px;color:#d1d5db;">RetinaGuard AI — HIPAA Compliant Medical Platform</p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Your RetinaGuard AI Verification Code"
        msg["From"] = f"RetinaGuard AI <{email_user}>"
        msg["To"] = to_email
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(email_user, email_pass)
            server.sendmail(email_user, to_email, msg.as_string())

        print(f"📧 Verification email successfully sent to {to_email}")
        return True
    except Exception as e:
        print(f"⚠️ Failed to send verification email to {to_email}: {e}")
        return False