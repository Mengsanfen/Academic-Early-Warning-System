"""
邮件发送工具模块
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from typing import Optional

from app.config import settings


def send_verification_email(to_email: str, code: str, expires_minutes: int = 5) -> bool:
    """
    发送验证码邮件

    Args:
        to_email: 收件人邮箱
        code: 验证码
        expires_minutes: 过期时间（分钟）

    Returns:
        bool: 是否发送成功
    """
    if not settings.EMAIL_ENABLED:
        # 未启用邮件发送，打印到控制台
        print(f"\n{'='*50}")
        print(f"[模拟邮件] 发送到: {to_email}")
        print(f"[模拟邮件] 验证码: {code}")
        print(f"[模拟邮件] 有效期: {expires_minutes}分钟")
        print(f"{'='*50}\n")
        return True

    try:
        # 调试信息
        print(f"[邮件调试] SMTP服务器: {settings.SMTP_HOST}:{settings.SMTP_PORT}")
        print(f"[邮件调试] 发件人: {settings.SMTP_FROM_EMAIL}")
        print(f"[邮件调试] 收件人: {to_email}")
        print(f"[邮件调试] 邮件启用状态: {settings.EMAIL_ENABLED}")

        # 创建邮件内容
        message = MIMEMultipart("alternative")

        # 使用Header正确编码中文主题
        subject = "密码找回验证码"
        message["Subject"] = Header(subject, "utf-8")

        # 发件人直接使用邮箱地址，避免中文编码问题
        message["From"] = settings.SMTP_FROM_EMAIL
        message["To"] = to_email

        # 纯文本内容
        text_content = f"""
您好！

您正在申请重置密码，验证码为：{code}

验证码有效期为 {expires_minutes} 分钟，请尽快使用。

如果您没有申请重置密码，请忽略此邮件。

此邮件由系统自动发送，请勿回复。
"""

        # HTML内容
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
</head>
<body style="font-family: 'Microsoft YaHei', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
        <h1 style="margin: 0;">密码找回验证码</h1>
    </div>
    <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; border: 1px solid #eee;">
        <p>您好！</p>
        <p>您正在申请重置密码，验证码为：</p>
        <div style="background: #fff; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0;">
            <span style="font-size: 32px; font-weight: bold; color: #667eea; letter-spacing: 8px;">{code}</span>
        </div>
        <p style="color: #999; font-size: 14px;">验证码有效期为 {expires_minutes} 分钟，请尽快使用。</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
        <p style="color: #999; font-size: 12px;">
            如果您没有申请重置密码，请忽略此邮件。<br>
            此邮件由系统自动发送，请勿回复。
        </p>
    </div>
</body>
</html>
"""

        # 添加邮件内容
        part1 = MIMEText(text_content, "plain", "utf-8")
        part2 = MIMEText(html_content, "html", "utf-8")
        message.attach(part1)
        message.attach(part2)

        # 发送邮件
        # 注意：设置 local_hostname 避免中文主机名导致的编码问题
        with smtplib.SMTP_SSL(
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            local_hostname="localhost"
        ) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, [to_email], message.as_string())

        print(f"[邮件发送成功] 收件人: {to_email}")
        return True

    except Exception as e:
        import traceback
        print(f"[邮件发送失败] 收件人: {to_email}, 错误: {str(e)}")
        traceback.print_exc()
        return False


def send_email(
    to_email: str,
    subject: str,
    content: str,
    html_content: Optional[str] = None
) -> bool:
    """
    发送普通邮件

    Args:
        to_email: 收件人邮箱
        subject: 邮件主题
        content: 邮件内容（纯文本）
        html_content: HTML内容（可选）

    Returns:
        bool: 是否发送成功
    """
    if not settings.EMAIL_ENABLED:
        print(f"\n[模拟邮件] 发送到: {to_email}")
        print(f"[模拟邮件] 主题: {subject}")
        print(f"[模拟邮件] 内容: {content}\n")
        return True

    try:
        message = MIMEMultipart("alternative")
        # 使用Header正确编码中文主题
        message["Subject"] = Header(subject, "utf-8")
        # 发件人直接使用邮箱地址，避免中文编码问题
        message["From"] = settings.SMTP_FROM_EMAIL
        message["To"] = to_email

        # 添加邮件内容
        message.attach(MIMEText(content, "plain", "utf-8"))
        if html_content:
            message.attach(MIMEText(html_content, "html", "utf-8"))

        with smtplib.SMTP_SSL(
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            local_hostname="localhost"
        ) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, [to_email], message.as_string())

        return True

    except Exception as e:
        print(f"[邮件发送失败] {str(e)}")
        return False
