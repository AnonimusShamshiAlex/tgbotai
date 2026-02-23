import logging
import os
import tempfile
import aiohttp
import asyncio
import speech_recognition as sr
from pydub import AudioSegment
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================
# ВАШИ ТОКЕНЫ
# ============================================
TELEGRAM_TOKEN = "8444193334:AAH6adrYZEg-id049jKtnl1sKkESuz25c4g"
OPENROUTER_API_KEY = "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"
MODEL_NAME = "arcee-ai/trinity-large-preview:free"

class AITelegramBot:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        
    async def get_ai_response(self, user_message: str) -> str:
        """Получение ответа от OpenRouter"""
        
        url = "https://openrouter.ai/api/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://t.me/your_bot",
            "X-Title": "AI Telegram Bot"
        }
        
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {
                    "role": "system",
                    "content": "Ты полезный помощник. Отвечай на русском языке кратко и по делу."
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        }
        
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    print(f"Статус ответа: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        try:
                            ai_response = data["choices"][0]["message"]["content"]
                            return ai_response
                        except Exception as e:
                            print(f"Ошибка парсинга: {e}")
                            return f"❌ Ошибка: {e}"
                    else:
                        error_text = await response.text()
                        print(f"Ошибка {response.status}: {error_text}")
                        return f"❌ Ошибка API: {response.status}"
                        
        except asyncio.TimeoutError:
            return "❌ Превышено время ожидания"
        except Exception as e:
            print(f"Ошибка соединения: {e}")
            return "❌ Ошибка соединения"
    
    async def process_voice(self, file_path: str) -> str:
        """Преобразование голоса в текст"""
        try:
            audio = AudioSegment.from_ogg(file_path)
            wav_path = file_path.replace('.ogg', '.wav')
            audio.export(wav_path, format="wav")
            
            with sr.AudioFile(wav_path) as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio_data = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio_data, language="ru-RU")
                return text
                
        except sr.UnknownValueError:
            return None
        except Exception as e:
            logger.error(f"Ошибка распознавания: {e}")
            return None
        finally:
            for f in [file_path, wav_path]:
                try:
                    if os.path.exists(f):
                        os.remove(f)
                except:
                    pass

# Создаем бота
bot = AITelegramBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 **AI Бот**\n\n"
        f"✅ Модель: {MODEL_NAME}\n"
        "✅ Понимаю голосовые сообщения\n"
        "✅ Говорю по-русски\n\n"
        "📝 Напиши мне что-нибудь"
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )
    
    response = await bot.get_ai_response(user_message)
    await update.message.reply_text(response)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("🎤 Обрабатываю голос...")
    
    try:
        voice_file = await context.bot.get_file(update.message.voice.file_id)
        
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            await voice_file.download_to_drive(tmp.name)
            temp_path = tmp.name
        
        text = await bot.process_voice(temp_path)
        
        if text:
            await status_msg.edit_text(f"📝 Распознано: {text}")
            
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action="typing"
            )
            
            response = await bot.get_ai_response(text)
            await update.message.reply_text(f"🤖 {response}")
        else:
            await status_msg.edit_text("❌ Не удалось распознать речь")
            
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await status_msg.edit_text("❌ Ошибка обработки")

def main():
    print("\n" + "="*60)
    print("🤖 ЗАПУСК БОТА")
    print("="*60)
    print(f"📱 Telegram Token: {TELEGRAM_TOKEN[:15]}...")
    print(f"🔑 OpenRouter Key: {OPENROUTER_API_KEY[:15]}...")
    print(f"🤖 Модель: {MODEL_NAME}")
    print("="*60 + "\n")
    
    try:
        # Создаем приложение
        app = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Добавляем обработчики
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        app.add_handler(MessageHandler(filters.VOICE, handle_voice))
        
        print("✅ Бот запущен!")
        print("📱 Отправьте /start боту в Telegram\n")
        
        # Запускаем
        app.run_polling()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        logger.error(f"Ошибка запуска: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n✅ Бот остановлен")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")