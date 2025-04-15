import cv2
import numpy as np
import os
import uuid
import tempfile
import easyocr
import logging
import asyncio
import time
import re
from typing import Optional, List, Dict, Any, Tuple, Union
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from deep_translator import GoogleTranslator
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import concurrent.futures
from io import BytesIO

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурационные переменные
TELEGRAM_BOT_TOKEN = "8061847198:AAHGZkfa06iQ1R16TnimfgKFT7Po0HkCu9Q"
SUPPORTED_LANGUAGES = {
    'ru': 'Russian',
    'en': 'English',
    'de': 'German',
    'fr': 'French',
    'es': 'Spanish',
    'it': 'Italian',
    'zh-CN': 'Chinese',
    'ja': 'Japanese',
    'ar': 'Arabic'
}

# Инициализация OCR-движков с разными конфигурациями
OCR_READERS = {
    'primary': easyocr.Reader(['ru', 'en']),
    'extended': None  # Будет загружен по необходимости
}

# Инициализация переводчиков
translators = {lang: GoogleTranslator(source='auto', target=lang) for lang in SUPPORTED_LANGUAGES.keys()}

class OCRProcessor:
    """Класс для обработки изображений и извлечения текста"""
    
    def __init__(self):
        self.readers = OCR_READERS
    
    async def process_image(self, image_path: str) -> Tuple[List[str], str, List[Dict]]:
        """Основной метод обработки изображения"""
        start_time = time.time()
        logger.info(f"Starting OCR processing for {image_path}")
        
        try:
            # Загрузка изображения
            original_image = cv2.imread(image_path)
            if original_image is None:
                raise ValueError("Не удалось прочитать изображение")
            
            # Базовая предобработка изображения
            h, w = original_image.shape[:2]
            max_dim = 2000
            if max(h, w) > max_dim:
                scale = max_dim / max(h, w)
                new_w, new_h = int(w * scale), int(h * scale)
                image = cv2.resize(original_image, (new_w, new_h), interpolation=cv2.INTER_AREA)
            else:
                image = original_image
            
            # Простое распознавание текста
            result = self.readers['primary'].readtext(image)
            
            # Если результатов не найдено, пробуем расширенные языки
            if not result and self.readers['extended'] is None:
                logger.info("No results with primary languages, trying extended language set")
                self.readers['extended'] = easyocr.Reader(['en', 'ru', 'de', 'fr', 'es', 'it'])
                result = self.readers['extended'].readtext(image)
            
            if not result:
                logger.warning("No text detected on the image")
                return ["Текст не обнаружен на изображении"], "Текст не обнаружен на изображении", []
            
            # Формирование итогового результата
            text_list = []
            details = []
            
            for item in result:
                bbox, text, confidence = item
                
                # Проверка, является ли результат валидным
                if not isinstance(text, str) or len(text.strip()) < 2:
                    continue
                
                if not isinstance(confidence, (int, float)) or confidence < 0.2:
                    continue
                    
                text_list.append(text)
                details.append({
                    "text": text,
                    "confidence": float(confidence),
                    "bbox": [[int(coord) for coord in point] for point in bbox]
                })
            
            full_text = "\n".join(text_list)
            
            logger.info(f"OCR processing completed in {time.time() - start_time:.2f} seconds")
            return text_list, full_text, details
            
        except Exception as e:
            logger.error(f"OCR processing error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return [], f"Ошибка распознавания: {str(e)}", []

def escape_markdown(text: str, version: str = 'v2') -> str:
    """
    Экранирует специальные символы Markdown для предотвращения ошибок парсинга
    """
    if version == 'v2':
        # Символы, требующие экранирования в MarkdownV2
        escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in escape_chars:
            text = text.replace(char, f'\\{char}')
    elif version == 'v1':
        # Упрощенное экранирование для Markdown V1
        text = text.replace('_', '\\_')
    
    return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команду /start"""
    user = update.effective_user
    logger.info(f"User {user.id} ({user.first_name}) started the bot")
    
    try:
        safe_name = escape_markdown(user.first_name or "User")
        
        await update.message.reply_text(
            f"👋 Привет, {safe_name}\\!\n\n"
            "Я OCR бот для распознавания текста с изображений и перевода\\.\n"
            "🔹 Отправь мне фотографию с текстом, и я извлеку из неё текст\n"
            "🔹 Затем ты сможешь перевести этот текст на другие языки\n\n"
            "Поддерживаемые языки для распознавания: русский и английский\n"
            "Поддерживаемые языки для перевода: 🇷🇺 🇬🇧 🇩🇪 🇫🇷 🇪🇸 🇮🇹 🇨🇳 🇯🇵 🇸🇦",
            parse_mode="MarkdownV2"
        )
        logger.info(f"Sent welcome message to user {user.id}")
    except Exception as e:
        logger.error(f"Error sending start message: {str(e)}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команду /help"""
    user = update.effective_user
    logger.info(f"User {user.id} requested help")
    
    try:
        await update.message.reply_text(
            "🔍 *Распознавание текста с изображений и перевод*\n\n"
            "📸 *Распознавание текста:*\n"
            "• Отправь мне фото с текстом\n"
            "• Я распознаю текст и дам возможность перевести его\n\n"
            "🌐 *Перевод:*\n"
            "• После распознавания текста, нажми на кнопку с нужным языком\n"
            "• Я переведу текст на выбранный язык\n\n"
            "💡 *Советы для лучшего распознавания:*\n"
            "• Убедись, что текст хорошо освещен\n"
            "• Избегай сильных теней на тексте\n"
            "• Фотографируй текст прямо, без наклона\n"
            "• Для документов лучше использовать режим «Документ» в камере\n\n"
            "🔄 *Команды:*\n"
            "/start \\- Начать общение с ботом\n"
            "/help \\- Показать это сообщение\n"
            "/languages \\- Показать поддерживаемые языки",
            parse_mode="MarkdownV2"
        )
        logger.info(f"Sent help message to user {user.id}")
    except Exception as e:
        logger.error(f"Error sending help message: {str(e)}")

async def languages_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команду /languages"""
    user = update.effective_user
    logger.info(f"User {user.id} requested languages list")
    
    try:
        languages_list = "\n".join([
            f"• {escape_markdown(code)} \\- {escape_markdown(name)}" 
            for code, name in SUPPORTED_LANGUAGES.items()
        ])
        
        await update.message.reply_text(
            "🌐 *Поддерживаемые языки:*\n\n"
            f"{languages_list}\n\n"
            "Для распознавания текста используются: русский и английский\n"
            "Для перевода доступны все перечисленные языки",
            parse_mode="MarkdownV2"
        )
        logger.info(f"Sent languages list to user {user.id}")
    except Exception as e:
        logger.error(f"Error sending languages list: {str(e)}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок для телеграм-бота"""
    logger.error(f"Exception while handling an update: {context.error}")
    
    import traceback
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    logger.error(f"Exception traceback:\n{tb_string}")
    
    if update and isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "😓 Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз."
        )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает фото от пользователя"""
    user = update.effective_user
    logger.info(f"Received photo from user {user.id}")
    
    processing_message = await update.message.reply_text("🔄 Обрабатываю изображение...")
    
    try:
        photo = update.message.photo[-1]
        photo_file = await context.bot.get_file(photo.file_id)
        
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}.jpg")
        
        await photo_file.download_to_drive(temp_file_path)
        
        ocr_processor = OCRProcessor()
        text_list, full_text, details = await ocr_processor.process_image(temp_file_path)
        
        context.user_data.update({"last_recognized_text": full_text})
        
        if text_list:
            keyboard = create_translation_keyboard()
            
            escaped_text = escape_markdown(full_text)
            
            await update.message.reply_text(
                f"✅ *Распознанный текст:*\n\n{escaped_text}\n\n"
                "Выберите язык для перевода:",
                reply_markup=keyboard,
                parse_mode="MarkdownV2"
            )
        else:
            await update.message.reply_text(
                "⚠️ Не удалось распознать текст на изображении.\n"
                "Попробуйте сделать фото с лучшим освещением или контрастом."
            )
        
        await processing_message.delete()
        
    except Exception as e:
        logger.error(f"Error processing photo: {str(e)}")
        await update.message.reply_text(
            f"❌ Произошла ошибка при обработке изображения: {str(e)}",
            parse_mode=None
        )
        if 'processing_message' in locals():
            await processing_message.delete()
    
    finally:
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            os.rmdir(temp_dir)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает документы от пользователя"""
    user = update.effective_user
    logger.info(f"Received document from user {user.id}")
    
    processing_message = await update.message.reply_text("🔄 Обрабатываю документ...")
    
    try:
        doc_file = await context.bot.get_file(update.message.document.file_id)
        
        file_name = update.message.document.file_name
        if not file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp', '.heic')):
            await update.message.reply_text(
                "⚠️ Пожалуйста, отправьте изображение в формате PNG, JPG, JPEG, BMP, TIFF, WEBP или HEIC."
            )
            await processing_message.delete()
            return
        
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}{os.path.splitext(file_name)[1]}")
        
        await doc_file.download_to_drive(temp_file_path)
        
        ocr_processor = OCRProcessor()
        text_list, full_text, details = await ocr_processor.process_image(temp_file_path)
        
        context.user_data.update({"last_recognized_text": full_text})
        
        if text_list:
            keyboard = create_translation_keyboard()
            
            escaped_text = escape_markdown(full_text)
            
            await update.message.reply_text(
                f"✅ *Распознанный текст:*\n\n{escaped_text}\n\n"
                "Выберите язык для перевода:",
                reply_markup=keyboard,
                parse_mode="MarkdownV2"
            )
        else:
            await update.message.reply_text(
                "⚠️ Не удалось распознать текст на изображении.\n"
                "Попробуйте сделать фото с лучшим освещением или контрастом."
            )
        
        await processing_message.delete()
        
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        await update.message.reply_text(
            f"❌ Произошла ошибка при обработке документа: {str(e)}",
            parse_mode=None
        )
        if 'processing_message' in locals():
            await processing_message.delete()
    
    finally:
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            os.rmdir(temp_dir)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает текстовые сообщения от пользователя"""
    user = update.effective_user
    text = update.message.text
    
    if len(text) > 3 and len(text) < 1000:
        context.user_data.update({"last_recognized_text": text})
        
        keyboard = create_translation_keyboard()
        
        await update.message.reply_text(
            "Хотите перевести этот текст? Выберите язык:",
            reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            "📸 Отправьте мне изображение с текстом для распознавания и перевода.\n"
            "Или отправьте короткий текст (до 1000 символов) для перевода."
        )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатия на кнопки (callback)"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    logger.info(f"Received callback from user {user.id}: {query.data}")
    
    try:
        if query.data.startswith('translate_'):
            lang_code = query.data.replace('translate_', '')
            
            if context.user_data and "last_recognized_text" in context.user_data:
                original_text = context.user_data["last_recognized_text"]
                
                processing_message = await query.message.reply_text(f"🔄 Перевожу на {SUPPORTED_LANGUAGES[lang_code]}...")
                
                try:
                    translated_text = translate_text(original_text, lang_code)
                    
                    escaped_translated = escape_markdown(translated_text)
                    
                    await query.message.reply_text(
                        f"🌐 *Перевод на {SUPPORTED_LANGUAGES[lang_code]}:*\n\n{escaped_translated}",
                        parse_mode="MarkdownV2"
                    )
                except Exception as e:
                    logger.error(f"Translation error: {str(e)}")
                    await query.message.reply_text(f"❌ Ошибка при переводе: {str(e)}")
                
                await processing_message.delete()
            else:
                await query.message.reply_text("⚠️ Не найден текст для перевода. Сначала отправьте изображение или текст.")
    except Exception as e:
        logger.error(f"Error handling callback: {str(e)}")
        await query.message.reply_text(f"❌ Произошла ошибка: {str(e)}")

def create_translation_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру с вариантами перевода"""
    keyboard = []
    row = []
    
    for i, (code, name) in enumerate(SUPPORTED_LANGUAGES.items()):
        emoji = get_flag_emoji(code)
        button = InlineKeyboardButton(f"{emoji} {name}", callback_data=f"translate_{code}")
        
        row.append(button)
        
        if (i + 1) % 3 == 0 or i == len(SUPPORTED_LANGUAGES) - 1:
            keyboard.append(row)
            row = []
    
    return InlineKeyboardMarkup(keyboard)

def get_flag_emoji(lang_code: str) -> str:
    """Получает эмодзи флага для кода языка"""
    flags = {
        'ru': '🇷🇺',
        'en': '🇬🇧',
        'de': '🇩🇪',
        'fr': '🇫🇷',
        'es': '🇪🇸',
        'it': '🇮🇹',
        'zh-CN': '🇨🇳',
        'ja': '🇯🇵',
        'ar': '🇸🇦'
    }
    return flags.get(lang_code, '🌐')

def translate_text(text: str, target_lang: str) -> str:
    """Переводит текст на целевой язык"""
    if not text or not target_lang:
        return "Нет текста для перевода"
    
    try:
        translator = translators.get(target_lang)
        if not translator:
            translator = GoogleTranslator(source='auto', target=target_lang)
            translators[target_lang] = translator
        
        max_chunk_size = 4500
        if len(text) <= max_chunk_size:
            return translator.translate(text)
        
        chunks = [text[i:i+max_chunk_size] for i in range(0, len(text), max_chunk_size)]
        translated_chunks = [translator.translate(chunk) for chunk in chunks]
        
        return ' '.join(translated_chunks)
    
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        return f"Ошибка перевода: {str(e)}"

async def main() -> None:
    """Запускает бота"""
    try:
        logger.info(f"Starting Telegram bot with token: {TELEGRAM_BOT_TOKEN[:5]}...[скрыто]")
        
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("languages", languages_command))
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        application.add_handler(CallbackQueryHandler(handle_callback))
        
        application.add_error_handler(error_handler)
        
        await application.initialize()
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        
        logger.info("✅ Telegram bot started successfully")
        
        while True:
            await asyncio.sleep(1)
    
    except Exception as e:
        logger.error(f"❌ Failed to start Telegram bot: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())