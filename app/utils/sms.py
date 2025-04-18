import httpx
from fastapi import HTTPException
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

P1SMS_API_URL = "https://admin.p1sms.ru/apiSms/create"
P1SMS_API_KEY = os.getenv("SMS_P1SMS_API_KEY")
P1SMS_SENDER = os.getenv("P1SMS_SENDER", "PANORAMIC")  # Имя отправителя

async def send_sms(phone: str, code: str):
    """
    Отправляет СМС с кодом верификации через P1SMS, используя шаблон.
    :param phone: Номер телефона в формате +7XXXXXXXXXX или 7XXXXXXXXXX
    :param code: Код верификации (например, '6807')
    :return: Ответ от P1SMS в формате JSON
    """
    if not P1SMS_API_KEY:
        raise HTTPException(status_code=500, detail="P1SMS API key not configured")

    # Удаляем все нечисловые символы из номера телефона
    clean_phone = ''.join(filter(str.isdigit, phone))
    if clean_phone.startswith('8'):
        clean_phone = '7' + clean_phone[1:]
    if len(clean_phone) != 11 or not clean_phone.startswith('7'):
        raise HTTPException(status_code=400, detail="Invalid phone number format")

    # Формируем текст сообщения, соответствующий шаблону
    message_text = f"Ваш код верификации из приложения PANORAMIC TENIS: {code}"

    # Формируем тело запроса
    sms_item = {
        "channel": "char",  # Буквенный канал
        "phone": clean_phone,
        "sender": P1SMS_SENDER,  # Отправитель PANORAMIC
        "text": message_text  # Текст, соответствующий шаблону
    }

    payload = {
        "apiKey": P1SMS_API_KEY,
        "sms": [sms_item]
    }

    logger.info(f"Sending SMS to {clean_phone} with payload: {payload}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(P1SMS_API_URL, json=payload)
            response.raise_for_status()
            json_response = response.json()
            logger.info(f"P1SMS response: {json_response}")

            if json_response.get("status") != "success":
                error_message = json_response.get("message", "Unknown error")
                raise HTTPException(
                    status_code=500,
                    detail=f"P1SMS error: {error_message}"
                )

            sms_data = json_response.get("data", [])
            if not sms_data or sms_data[0].get("status") not in ["sent", "queued"]:
                status = sms_data[0].get("status", "Unknown status") if sms_data else "No data"
                raise HTTPException(
                    status_code=500,
                    detail=f"P1SMS failed to send SMS: {status}"
                )

            return json_response
        except httpx.HTTPStatusError as e:
            logger.error(f"P1SMS HTTP error: {e}")
            logger.error(f"Response content: {e.response.text}")
            raise HTTPException(status_code=500, detail=f"P1SMS request failed: {str(e)}")
        except Exception as e:
            logger.error(f"P1SMS unexpected error: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to send SMS: {str(e)}")