import telebot
import requests
import jsons
import re
from Class_ModelResponse import ModelResponse
user_context = {}

API_TOKEN = 'token'
bot = telebot.TeleBot(API_TOKEN)

# Команды
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "Привет! Я ваш Telegram бот.\n"
        "Доступные команды:\n"
        "/start - вывод всех доступных команд\n"
        "/model - выводит название используемой языковой модели\n"
        "/clear - очищает контекст\n"
        "/context - выводит текущий контекст\n"
        "Отправьте любое сообщение, и я отвечу с помощью LLM модели."
    )
    bot.reply_to(message, welcome_text)


@bot.message_handler(commands=['model'])
def send_model_name(message):
    response = requests.get('http://localhost:1234/v1/models')

    if response.status_code == 200:
        model_info = response.json()
        model_name = model_info['data'][0]['id']
        bot.reply_to(message, f"Используемая модель: {model_name}")
    else:
        bot.reply_to(message, 'Не удалось получить информацию о модели.')

@bot.message_handler(commands=['clear'])
def clear_context(message):
   
    user_id = message.from_user.id
    if user_id in user_context:
        del user_context[user_id]
        bot.reply_to(message, 'Контекст очищен!')
    else:
        bot.reply_to(message, 'Контекст ещё не был установлен.')

@bot.message_handler(commands=['context'])
def show_context(message):
    user_id = message.from_user.id
    context = user_context.get(user_id, [])
    context_output = "\n".join([f"{item['role']}: {item['content']}" for item in context])
    
    if context_output:
        bot.reply_to(message, f"Ваш текущий контекст:\n{context_output}")
    else:
        bot.reply_to(message, 'Контекст пуст или не был установлен.')

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    user_query = message.text

    context = user_context.get(user_id, []).copy() 

    context_with_instruction = context + [
        {"role": "user", "content": user_query + " (Пожалуйста, ответь по-русски.)"}
    ]

    request = {
        "messages": context_with_instruction
    }

    response = requests.post(
        'http://localhost:1234/v1/chat/completions',
        json=request
    )

    if response.status_code == 200:
        model_response: ModelResponse = jsons.loads(response.text, ModelResponse)
        assistant_reply = model_response.choices[0].message.content
        cleaned_reply = re.sub(r"<think>.*?</think>", "", assistant_reply, flags=re.DOTALL).strip()
        context.append({"role": "user", "content": user_query})
        context.append({"role": "assistant", "content": cleaned_reply})

        user_context[user_id] = context

        bot.reply_to(message, cleaned_reply)
    else:
        bot.reply_to(message, 'Произошла ошибка при обращении к модели.')


# Запуск бота
if __name__ == '__main__':
    bot.polling(none_stop=True)
