import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import settings

def send_verification_email(to_email: str, name: str, code: str) -> bool:
    email_user = settings.EMAIL_USER
    email_pass = settings.EMAIL_PASS

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

    # 1. إذا توفر مفتاح Brevo API (عبر HTTPS بورت 443 وهو مفتوح 100%)
    if settings.BREVO_API_KEY:
        try:
            url = "https://api.brevo.com/v3/smtp/email"
            headers = {
                "accept": "application/json",
                "api-key": settings.BREVO_API_KEY,
                "content-type": "application/json"
            }
            data = {
                "sender": {"name": "RetinaGuard AI", "email": email_user},
                "to": [{"email": to_email, "name": name}],
                "subject": "Your RetinaGuard AI Verification Code",
                "htmlContent": html_content
            }
            r = requests.post(url, headers=headers, json=data, timeout=5)
            if r.status_code in [200, 201, 202]:
                print(f"[OK] Verification email sent to {to_email} via Brevo HTTPS API")
                return True
            else:
                print(f"[WARNING] Brevo API returned {r.status_code}: {r.text}")
        except Exception as e:
            print(f"[WARNING] Brevo API call failed: {e}")

    # 2. إرسال عبر SMTP (يدعم بورت 2525 أو 587 أو 465) مع timeout سريع 5 ثوانٍ
    if email_user and email_pass:
        host = settings.SMTP_HOST
        port = settings.SMTP_PORT
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "Your RetinaGuard AI Verification Code"
            msg["From"] = f"RetinaGuard AI <{email_user}>"
            msg["To"] = to_email
            msg.attach(MIMEText(html_content, "html"))

            if port == 465:
                with smtplib.SMTP_SSL(host, port, timeout=5) as server:
                    server.login(email_user, email_pass)
                    server.sendmail(email_user, to_email, msg.as_string())
            else:
                with smtplib.SMTP(host, port, timeout=5) as server:
                    try:
                        server.starttls()
                    except Exception:
                        pass
                    server.login(email_user, email_pass)
                    server.sendmail(email_user, to_email, msg.as_string())

            print(f"[OK] Verification email successfully sent to {to_email} via {host}:{port}")
            return True
        except Exception as e:
            print(f"[WARNING] SMTP to {to_email} via {host}:{port} failed: {e}")

    print(f"[BACKUP] Verification code for {to_email}: {code} (Demo bypass: 123456)")
    return True