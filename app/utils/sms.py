import httpx
from fastapi import HTTPException
import os

P1SMS_API_URL = "https://admin.p1sms.ru/apiSms/create"
P1SMS_API_KEY = os.getenv("SMS_P1SMS_API_KEY")

async def send_sms(phone: str, message: str):
    """
    Отправляет СМС на указанный номер через P1SMS.
    :param phone: Номер телефона в формате +7XXXXXXXXXX или 7XXXXXXXXXX
    :param message: Текст сообщения
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

    # Формируем тело запроса
    payload = {
        "apiKey": P1SMS_API_KEY,
        "sms": [
            {
                "channel": "digit",  # Цифровой канал для кодов верификации
                "phone": clean_phone,
                "text": message
            }
        ]
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(P1SMS_API_URL, json=payload)
            response.raise_for_status()
            json_response = response.json()
            print(f"P1SMS response: {json_response}")

            if json_response.get("status") != "success":
                error_message = json_response.get("message", "Unknown error")
                raise HTTPException(
                    status_code=500,
                    detail=f"P1SMS error: {error_message}"
                )

            # Проверяем статус отправленного сообщения
            sms_data = json_response.get("data", [])
            if not sms_data or sms_data[0].get("status") not in ["sent", "queued"]:
                raise HTTPException(
                    status_code=500,
                    detail=f"P1SMS failed to send SMS: {sms_data[0].get('status', 'Unknown status')}"
                )

            return json_response
        except httpx.HTTPStatusError as e:
            print(f"P1SMS HTTP error: {e}")
            raise HTTPException(status_code=500, detail=f"P1SMS request failed: {str(e)}")
        except Exception as e:
            print(f"P1SMS unexpected error: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to send SMS: {str(e)}")