import cv2
import numpy as np
import os
import uuid
import tempfile
import easyocr
import logging
import asyncio
from typing import Optional, List, Dict, Any, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from deep_translator import GoogleTranslator
from PIL import Image, ImageEnhance, ImageFilter

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration variables
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

# OCR readers for different language sets
OCR_READERS = {
    'primary': easyocr.Reader(['ru', 'en']),
    'extended': None  # Will be lazily loaded when needed
}

# Create translator instances
translators = {lang: GoogleTranslator(source='auto', target=lang) for lang in SUPPORTED_LANGUAGES.keys()}

def escape_markdown(text: str, version: str = 'v2') -> str:
    """
    Escape special characters that have meaning in Markdown to prevent parsing errors.
    
    :param text: Text to escape
    :param version: Markdown version ('v2' or 'v1')
    :return: Escaped text
    """
    if version == 'v2':
        # Characters that need escaping in MarkdownV2
        escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in escape_chars:
            text = text.replace(char, f'\\{char}')
    elif version == 'v1':
        # Simpler escaping for Markdown V1
        text = text.replace('_', '\\_')
    
    return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"User {user.id} ({user.first_name}) started the bot")
    
    try:
        # Escape the user's first name and all special characters
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
    user = update.effective_user
    logger.info(f"User {user.id} requested languages list")
    
    try:
        # Escape each language code and name
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
    logger.error(f"Exception while handling an update: {context.error}")
    
    import traceback
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    logger.error(f"Exception traceback:\n{tb_string}")
    
    # Notify user about error if possible
    if update and isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "😓 Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз."
        )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"Received photo from user {user.id}")
    
    processing_message = await update.message.reply_text("🔄 Обрабатываю изображение...")
    
    try:
        photo = update.message.photo[-1]
        photo_file = await context.bot.get_file(photo.file_id)
        
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}.jpg")
        
        await photo_file.download_to_drive(temp_file_path)
        
        # Process the image with enhanced OCR
        text_list, full_text, details = await process_image_with_enhanced_ocr(temp_file_path)
        
        # Use dictionary method to set data
        context.user_data.update({"last_recognized_text": full_text})
        
        if text_list:
            # Create keyboard with translation options
            keyboard = create_translation_keyboard()
            
            await update.message.reply_text(
                f"✅ *Распознанный текст:*\n\n{full_text}\n\n"
                "Выберите язык для перевода:",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "⚠️ Не удалось распознать текст на изображении.\n"
                "Попробуйте сделать фото с лучшим освещением или контрастом."
            )
        
        await processing_message.delete()
        
    except Exception as e:
        logger.error(f"Error processing photo: {str(e)}")
        await update.message.reply_text(f"❌ Произошла ошибка при обработке изображения: {str(e)}")
        if 'processing_message' in locals():
            await processing_message.delete()
    
    finally:
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            os.rmdir(temp_dir)

def escape_markdown(text: str) -> str:
    """
    Escape special characters that have meaning in Markdown to prevent parsing errors.
    """
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
                    # Translate the text
                    translated_text = translate_text(original_text, lang_code)
                    
                    # Escape markdown characters in both original and translated text
                    escaped_original = escape_markdown(original_text)
                    escaped_translated = escape_markdown(translated_text)
                    
                    await query.message.reply_text(
                        f"📝 *Оригинальный текст:*\n\n{escaped_original}\n\n"
                        f"🌐 *Перевод на {SUPPORTED_LANGUAGES[lang_code]}:*\n\n{escaped_translated}",
                        parse_mode="MarkdownV2"
                    )
                except Exception as e:
                    logger.error(f"Translation error: {str(e)}")
                    # Use plain text if Markdown parsing fails
                    await query.message.reply_text(
                        f"❌ Ошибка при переводе: {str(e)}",
                        parse_mode=None
                    )
                
                await processing_message.delete()
            else:
                await query.message.reply_text(
                    "⚠️ Не найден текст для перевода. Сначала отправьте изображение или текст.",
                    parse_mode=None
                )
    except Exception as e:
        logger.error(f"Error handling callback: {str(e)}")
        await query.message.reply_text(
            f"❌ Произошла ошибка: {str(e)}",
            parse_mode=None
        )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"Received photo from user {user.id}")
    
    processing_message = await update.message.reply_text("🔄 Обрабатываю изображение...")
    
    try:
        photo = update.message.photo[-1]
        photo_file = await context.bot.get_file(photo.file_id)
        
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}.jpg")
        
        await photo_file.download_to_drive(temp_file_path)
        
        # Process the image with enhanced OCR
        text_list, full_text, details = await process_image_with_enhanced_ocr(temp_file_path)
        
        # Use dictionary method to set data
        context.user_data.update({"last_recognized_text": full_text})
        
        if text_list:
            # Create keyboard with translation options
            keyboard = create_translation_keyboard()
            
            # Escape markdown characters in the text
            escaped_text = escape_markdown(full_text)
            
            await update.message.reply_text(
                f"✅ *Распознанный текст:*\n\n{escaped_text}\n\n"
                "Выберите язык для перевода:",
                reply_markup=keyboard,
                parse_mode="MarkdownV2"  # Use MarkdownV2 which requires escaping
            )
        else:
            await update.message.reply_text(
                "⚠️ Не удалось распознать текст на изображении.\n"
                "Попробуйте сделать фото с лучшим освещением или контрастом."
            )
        
        await processing_message.delete()
        
    except Exception as e:
        logger.error(f"Error processing photo: {str(e)}")
        # Use a plain text message to avoid Markdown parsing issues
        await update.message.reply_text(
            f"❌ Произошла ошибка при обработке изображения: {str(e)}",
            parse_mode=None  # Disable parsing
        )
        if 'processing_message' in locals():
            await processing_message.delete()
    
    finally:
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            os.rmdir(temp_dir)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        
        # Process the image with enhanced OCR
        text_list, full_text, details = await process_image_with_enhanced_ocr(temp_file_path)
        
        # Use dictionary method to set data
        context.user_data.update({"last_recognized_text": full_text})
        
        if text_list:
            # Create keyboard with translation options
            keyboard = create_translation_keyboard()
            
            # Escape markdown characters in the text
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
        # Use a plain text message to avoid Markdown parsing issues
        await update.message.reply_text(
            f"❌ Произошла ошибка при обработке документа: {str(e)}",
            parse_mode=None  # Disable parsing
        )
        if 'processing_message' in locals():
            await processing_message.delete()
    
    finally:
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            os.rmdir(temp_dir)
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    text = update.message.text
    
    # If it's a short text, store it for translation
    if len(text) > 3 and len(text) < 1000:
        # Use dictionary method to set data
        context.user_data.update({"last_recognized_text": text})
        
        # Create keyboard with translation options
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
                    # Translate the text
                    translated_text = translate_text(original_text, lang_code)
                    
                    await query.message.reply_text(
                        f"🌐 *Перевод на {SUPPORTED_LANGUAGES[lang_code]}:*\n\n{translated_text}",
                        parse_mode="Markdown"
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

async def process_image_with_enhanced_ocr(image_path: str) -> Tuple[List[str], str, List[Dict]]:
    """Enhanced OCR processing with multiple preprocessing techniques"""
    try:
        # Read image
        original_image = cv2.imread(image_path)
        if original_image is None:
            raise ValueError("Не удалось прочитать изображение")
        
        # Try multiple preprocessing techniques and combine results
        results = []
        confidences = []
        
        # 1. Original image
        result1 = OCR_READERS['primary'].readtext(original_image)
        if result1:
            results.extend(result1)
            confidences.extend([r[2] for r in result1])

        # 2. Enhanced contrast and sharpness
        enhanced_image = enhance_image_quality(image_path)
        result2 = OCR_READERS['primary'].readtext(enhanced_image)
        if result2:
            # Only add new texts that weren't detected before
            existing_texts = [r[1].lower() for r in results]
            for r in result2:
                if r[1].lower() not in existing_texts and r[2] > 0.3:
                    results.append(r)
                    confidences.append(r[2])
        
        # 3. Try grayscale with adaptive threshold
        gray = cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        result3 = OCR_READERS['primary'].readtext(thresh)
        if result3:
            existing_texts = [r[1].lower() for r in results]
            for r in result3:
                if r[1].lower() not in existing_texts and r[2] > 0.3:
                    results.append(r)
                    confidences.append(r[2])
                    
        # If no results from primary languages, try with extended set (lazy loading)
        if not results and OCR_READERS['extended'] is None:
            logger.info("No results with primary languages, trying extended language set")
            # Lazy load extended language reader
            OCR_READERS['extended'] = easyocr.Reader(['en', 'ru', 'de', 'fr', 'es', 'it'])
            
            # Try with extended languages
            result_ext = OCR_READERS['extended'].readtext(original_image)
            if result_ext:
                results.extend(result_ext)
                confidences.extend([r[2] for r in result_ext])
        
        # Filter and process results
        if not results:
            return ["Текст не обнаружен на изображении"], "Текст не обнаружен на изображении", []
        
        # Filter by confidence and sort by position
        filtered_results = [r for r in results if r[2] > 0.2]
        sorted_results = sort_results_by_position(filtered_results)
        
        # Group by lines for better structure
        grouped_results = group_by_lines(sorted_results)
        
        # Create result data
        text_list = []
        for group in grouped_results:
            line = " ".join([clean_text(item[1]) for item in group])
            if line.strip():
                text_list.append(line)
        
        full_text = "\n".join(text_list)
        
        # Create detailed output
        details = []
        for result in sorted_results:
            bbox, text, confidence = result
            details.append({
                "text": clean_text(text),
                "confidence": float(confidence),
                "bbox": [[int(coord) for coord in point] for point in bbox]
            })
        
        return text_list, full_text, details
        
    except Exception as e:
        logger.error(f"OCR processing error: {str(e)}")
        import traceback
        traceback.print_exc()
        return [], f"Ошибка распознавания: {str(e)}", []

def enhance_image_quality(image_path: str) -> np.ndarray:
    """Enhance image quality for better OCR using PIL and OpenCV"""
    try:
        # Open with PIL for enhancement
        with Image.open(image_path) as img:
            # Convert to RGB if in RGBA mode
            if img.mode == 'RGBA':
                img = img.convert('RGB')
                
            # Apply enhancements
            contrast = ImageEnhance.Contrast(img).enhance(1.5)
            sharpness = ImageEnhance.Sharpness(contrast).enhance(2.0)
            brightness = ImageEnhance.Brightness(sharpness).enhance(1.2)
            
            # Apply a slight unsharp mask to improve edge detection
            enhanced = brightness.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
            
            # Convert to OpenCV format
            enhanced_np = np.array(enhanced)
            enhanced_cv = cv2.cvtColor(enhanced_np, cv2.COLOR_RGB2BGR)
            
            return enhanced_cv
    except Exception as e:
        logger.error(f"Image enhancement error: {str(e)}")
        # Return original image using OpenCV if enhancement fails
        return cv2.imread(image_path)

def preprocess_image(image: np.ndarray) -> np.ndarray:
    """Apply preprocessing to image for better OCR results"""
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply different preprocessing techniques and select the best one based on OCR results
    preprocessed_images = []
    
    # 1. Adaptive Gaussian Thresholding
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    preprocessed_images.append(binary)
    
    # 2. CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    preprocessed_images.append(enhanced)
    
    # 3. Denoising
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    preprocessed_images.append(denoised)
    
    # 4. Sharpening
    kernel = np.array([[-1,-1,-1], [-1, 9,-1], [-1,-1,-1]])
    sharpened = cv2.filter2D(gray, -1, kernel)
    preprocessed_images.append(sharpened)
    
    # 5. Otsu's Thresholding
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    preprocessed_images.append(otsu)
    
    return enhanced  # Return the CLAHE enhanced version by default

def clean_text(text: str) -> str:
    """Clean and normalize the recognized text"""
    import re
    
    # Remove extra spaces
    cleaned = ' '.join(text.split())
    
    # Remove common OCR artifacts and unwanted characters
    artifacts = ["[", "]", "{", "}", "~", "|", "^", "*", "+", "=", "\\", "/"]
    for artifact in artifacts:
        cleaned = cleaned.replace(artifact, "")
    
    # Normalize quotes and apostrophes
    cleaned = cleaned.replace("\"", "\"").replace("\'", "'").replace("''", '"').replace("``", '"')
    
    # Fix common OCR errors
    cleaned = cleaned.replace("0", "O").replace("l", "I")
    
    # Remove non-printable characters
    cleaned = re.sub(r'[^\x20-\x7E\u0400-\u04FF\n]', '', cleaned)
    
    return cleaned

def sort_results_by_position(results: List) -> List:
    """Sort OCR results by position (top to bottom, left to right)"""
    return sorted(results, key=lambda r: (r[0][0][1], r[0][0][0]))

def group_by_lines(results: List) -> List[List]:
    """Group OCR results by lines based on y-coordinate proximity"""
    if not results:
        return []
    
    # Calculate average height of bounding boxes
    heights = [
        max(r[0][2][1], r[0][3][1]) - min(r[0][0][1], r[0][1][1])
        for r in results
    ]
    avg_height = sum(heights) / len(heights) if heights else 20
    
    # Group results by lines
    groups = []
    current_group = [results[0]]
    
    for i in range(1, len(results)):
        current_bbox = results[i][0]
        prev_bbox = results[i-1][0]
        
        current_center_y = (current_bbox[0][1] + current_bbox[2][1]) / 2
        prev_center_y = (prev_bbox[0][1] + prev_bbox[2][1]) / 2
        
        # If the current result is close enough to the previous one vertically,
        # add it to the current group
        if abs(current_center_y - prev_center_y) < avg_height * 0.7:
            current_group.append(results[i])
        else:
            # Otherwise, start a new group
            current_group.sort(key=lambda r: r[0][0][0])  # Sort group by x-coordinate
            groups.append(current_group)
            current_group = [results[i]]
    
    # Add the last group if it exists
    if current_group:
        current_group.sort(key=lambda r: r[0][0][0])
        groups.append(current_group)
    
    return groups

def create_translation_keyboard() -> InlineKeyboardMarkup:
    """Create a keyboard with translation language options"""
    keyboard = []
    row = []
    
    for i, (code, name) in enumerate(SUPPORTED_LANGUAGES.items()):
        # Create buttons with flag emojis where available
        emoji = get_flag_emoji(code)
        button = InlineKeyboardButton(f"{emoji} {name}", callback_data=f"translate_{code}")
        
        row.append(button)
        
        # Create rows with 3 buttons each
        if (i + 1) % 3 == 0 or i == len(SUPPORTED_LANGUAGES) - 1:
            keyboard.append(row)
            row = []
    
    return InlineKeyboardMarkup(keyboard)

def get_flag_emoji(lang_code: str) -> str:
    """Get flag emoji for a language code"""
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
    """Translate text to the target language"""
    if not text or not target_lang:
        return "Нет текста для перевода"
    
    try:
        # Use the pre-initialized translator
        translator = translators.get(target_lang)
        if not translator:
            # Create a new translator if not found
            translator = GoogleTranslator(source='auto', target=target_lang)
            translators[target_lang] = translator
        
        # Handle long texts by splitting into chunks (Google Translator API has limits)
        max_chunk_size = 4500
        if len(text) <= max_chunk_size:
            return translator.translate(text)
        
        # Split into chunks and translate
        chunks = [text[i:i+max_chunk_size] for i in range(0, len(text), max_chunk_size)]
        translated_chunks = [translator.translate(chunk) for chunk in chunks]
        
        return ' '.join(translated_chunks)
    
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        return f"Ошибка перевода: {str(e)}"

async def main() -> None:
    """Start the bot."""
    try:
        logger.info(f"Starting Telegram bot with token: {TELEGRAM_BOT_TOKEN[:5]}...[скрыто]")
        
        # Create the Application
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Register handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("languages", languages_command))
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        application.add_handler(CallbackQueryHandler(handle_callback))
        
        # Register error handler
        application.add_error_handler(error_handler)
        
        # Start the Bot
        await application.initialize()
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        
        logger.info("✅ Telegram bot started successfully")
        
        # Use a different approach to keep the bot running
        while True:
            await asyncio.sleep(1)
    
    except Exception as e:
        logger.error(f"❌ Failed to start Telegram bot: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())