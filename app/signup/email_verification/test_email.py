import asyncio
import logging
from app.signup.email_verification.sending_email import send_verification_email
from app.data.config import settings

# Настраиваем логи, чтобы видеть детали
logging.basicConfig(level=logging.INFO)


async def test_mail():
    print(f"Попытка отправки от имени: {settings.GMAIL_USER}")

    subject = "Тестовая проверка системы"
    recipient = "oleg_zolotarev_0@mail.ru"  # Отправь самому себе
    text = "Если ты это видишь, значит SMTP настроен верно!"
    html = "<h1>Успех!</h1><p>Система верификации готова к работе.</p>"

    try:
        await send_verification_email(
            recipient_email=recipient,
            subject=subject,
            plain_text=text,
            html_content=html
        )
        print("✅ Письмо успешно отправлено!")
    except Exception as e:
        print(f"❌ Ошибка при отправке: {e}")


if __name__ == "__main__":
    asyncio.run(test_mail())