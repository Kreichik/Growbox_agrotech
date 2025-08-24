import requests
import os
from dotenv import load_dotenv

load_dotenv()

DEFAULT_SYSTEM_PROMPT = "Ты — полезный и дружелюбный ассистент. Отвечай кратко и по делу."

api_key = os.getenv("MISTRAL_TOKEN")

api_url = "https://api.mistral.ai/v1/chat/completions"


def completeChat(prompt: str, history: list, model: str = "mistral-large-latest") -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    messages_to_send = list(history)
    messages_to_send.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages_to_send
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()

        if result.get('choices'):
            assistant_response = result['choices'][0]['message']['content'].strip()
            return assistant_response
        else:
            return "Не удалось получить ответ."

    except requests.exceptions.RequestException as e:
        print(f"Ошибка API: {e}")
        return "Ошибка подключения к ИИ."
    except (KeyError, IndexError) as e:
        print(f"Ошибка обработки ответа: {e}")
        return "Неверный формат ответа от ИИ."