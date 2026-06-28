import logging
import os
import tempfile
import asyncio
import aiohttp
import speech_recognition as sr
from pydub import AudioSegment

# ============================================
# УКАЗЫВАЕМ ПУТЬ К FFMPEG
# ============================================
AudioSegment.ffmpeg = r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"

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
MODEL_NAME = "google/gemma-4-26b-a4b-it"

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
                    if response.status == 200:
                        data = await response.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        error_text = await response.text()
                        return f"❌ Ошибка API: {response.status} - {error_text[:100]}"
        except asyncio.TimeoutError:
            return "❌ Превышено время ожидания"
        except Exception as e:
            print(f"Ошибка: {e}")
            return f"❌ Ошибка: {str(e)[:100]}"
    
    async def process_voice(self, file_path: str) -> str:
        """Преобразование голоса в текст"""
        wav_path = None  # Инициализируем переменную
        
        try:
            # Конвертируем OGG в WAV
            audio = AudioSegment.from_ogg(file_path)
            wav_path = file_path.replace('.ogg', '.wav')
            audio.export(wav_path, format="wav")
            
            # Распознаем речь
            with sr.AudioFile(wav_path) as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio_data = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio_data, language="ru-RU")
                return text
                
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"Ошибка сервиса распознавания: {e}")
            return None
        except Exception as e:
            logger.error(f"Ошибка распознавания: {e}")
            return None
        finally:
            # Удаляем временные файлы
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
            
            try:
                if wav_path and os.path.exists(wav_path):
                    os.remove(wav_path)
            except:
                pass

# Создаем бота
bot = AITelegramBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 **AI Бот**\n\n"
        f"✅ Модель: {MODEL_NAME}\n"
        "✅ Понимаю голосовые сообщения\n"
        "✅ Работаю с текстом\n"
        "✅ Говорю по-русски\n\n"
        "📝 Напиши или скажи мне что-нибудь"
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    # Отправляем статус "печатает"
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )
    
    # Получаем ответ от ИИ
    response = await bot.get_ai_response(user_message)
    
    # Отправляем ответ
    await update.message.reply_text(response)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка голосовых сообщений"""
    status_msg = await update.message.reply_text("🎤 Обрабатываю голосовое сообщение...")
    
    try:
        # Скачиваем голосовое сообщение
        voice_file = await context.bot.get_file(update.message.voice.file_id)
        
        # Сохраняем во временный файл
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            await voice_file.download_to_drive(tmp.name)
            temp_path = tmp.name
        
        # Распознаем речь
        text = await bot.process_voice(temp_path)
        
        if text:
            await status_msg.edit_text(f"📝 Распознано: \"{text}\"")
            
            # Отправляем статус "печатает"
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action="typing"
            )
            
            # Получаем ответ от ИИ
            response = await bot.get_ai_response(text)
            
            # Отправляем ответ
            await update.message.reply_text(f"🤖 {response}")
        else:
            await status_msg.edit_text("❌ Не удалось распознать речь. Попробуйте говорить четче или отправьте текстовое сообщение.")
            
    except Exception as e:
        logger.error(f"Ошибка обработки голоса: {e}")
        await status_msg.edit_text(f"❌ Ошибка обработки голосового сообщения: {str(e)[:100]}")

def main():
    print("\n" + "="*60)
    print("🤖 ЗАПУСК БОТА")
    print("="*60)
    print(f"📱 Telegram Token: {TELEGRAM_TOKEN[:15]}...")
    print(f"🔑 OpenRouter Key: {OPENROUTER_API_KEY[:15]}...")
    print(f"🤖 Модель: {MODEL_NAME}")
    print("="*60 + "\n")
    
    try:
        # СОЗДАЕМ ПРИЛОЖЕНИЕ
        app = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Добавляем обработчики
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        app.add_handler(MessageHandler(filters.VOICE, handle_voice))
        
        print("✅ Бот запущен!")
        print("📱 Отправьте /start боту в Telegram")
        print("🎤 Бот принимает голосовые сообщения\n")
        print("Нажмите Ctrl+C для остановки")
        print("-" * 60)
        
        # ЗАПУСКАЕМ
        app.run_polling(allowed_updates=["message", "voice"])
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        logger.error(f"Ошибка запуска: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✅ Бот остановлен")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")