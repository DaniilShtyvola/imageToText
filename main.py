from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import easyocr
import cv2
import numpy as np
import json
import base64
import uuid
import tempfile
import os
import shutil
import asyncio
import logging
from typing import Optional, List, Dict, Any
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = "8061847198:AAHGZkfa06iQ1R16TnimfgKFT7Po0HkCu9Q" 

app = FastAPI(
    title="OCR API with Telegram Bot",
    description="API для распознавания текста из изображений с помощью EasyOCR и Telegram бота",
    version="1.0.0",
    contact={
        "name": "OCR API Support",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT License",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

reader = easyocr.Reader(['ru', 'en'])

class Base64Image(BaseModel):
    base64_image: str = Field(..., 
                             description="Строка base64 изображения без префикса data:image/...")
    filename: Optional[str] = Field(None, 
                                  description="Опциональное имя файла")
    
    class Config:
        schema_extra = {
            "example": {
                "base64_image": "/9j/4AAQSkZJRgABAQEASABIAAD...",
                "filename": "test_image.jpg"
            }
        }

class OCRResult(BaseModel):
    text: List[str] = Field(..., 
                          description="Список распознанных текстовых строк")
    
    class Config:
        schema_extra = {
            "example": {
                "text": ["Распознанная строка 1", "Распознанная строка 2"]
            }
        }

class OCRDetailedResult(BaseModel):
    text: List[str] = Field(..., description="Список распознанных текстовых строк")
    full_text: str = Field(..., description="Полный распознанный текст с сохранением переносов строк")
    details: List[Dict[str, Any]] = Field(..., description="Детальная информация о каждом распознанном блоке текста")
    
    class Config:
        schema_extra = {
            "example": {
                "text": ["Распознанная строка 1", "Распознанная строка 2"],
                "full_text": "Распознанная строка 1\nРаспознанная строка 2",
                "details": [
                    {"text": "Распознанная строка 1", "confidence": 0.99, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]},
                    {"text": "Распознанная строка 2", "confidence": 0.95, "bbox": [[10, 40], [100, 40], [100, 60], [10, 60]]}
                ]
            }
        }

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"User {user.id} ({user.first_name}) started the bot")
    
    try:
        await update.message.reply_text(
            f"Привет, {user.first_name}! 👋\n\n"
            "Я OCR бот для распознавания текста с изображений.\n"
            "Отправь мне фотографию с текстом, и я извлеку из неё текст.\n\n"
            "Поддерживаются русский и английский языки."
        )
        logger.info(f"Sent welcome message to user {user.id}")
    except Exception as e:
        logger.error(f"Error sending start message: {str(e)}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"User {user.id} requested help")
    
    try:
        await update.message.reply_text(
            "🔍 *Распознавание текста с изображений*\n\n"
            "Просто отправь мне фото с текстом, и я верну распознанный текст.\n"
            "Поддерживаются русский и английский языки.\n\n"
            "Советы для лучшего распознавания:\n"
            "• Убедитесь, что текст хорошо освещен\n"
            "• Избегайте сильных теней на тексте\n"
            "• Фотографируйте текст прямо, без наклона\n"
            "• Для документов лучше использовать режим «Документ» в камере",
            parse_mode="Markdown"
        )
        logger.info(f"Sent help message to user {user.id}")
    except Exception as e:
        logger.error(f"Error sending help message: {str(e)}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Exception while handling an update: {context.error}")
    
    import traceback
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    logger.error(f"Exception traceback:\n{tb_string}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    photo = update.message.photo[-1]
    
    processing_message = await update.message.reply_text("Обрабатываю изображение...")

    try:
        photo_file = await context.bot.get_file(photo.file_id)
        
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}.jpg")
        
        await photo_file.download_to_drive(temp_file_path)
        
        text_list, full_text, details = process_image_detailed(temp_file_path)
        
        if text_list:
            response_text = f"Распознанный текст:\n\n{full_text}"
        else:
            response_text = "Не удалось распознать текст на изображении."
        
        await update.message.reply_text(response_text)
        
        await processing_message.delete()
        
    except Exception as e:
        logger.error(f"Error processing Telegram photo: {str(e)}")
        await update.message.reply_text(f"Произошла ошибка при обработке изображения: {str(e)}")
        await processing_message.delete()
    
    finally:
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            os.rmdir(temp_dir)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    processing_message = await update.message.reply_text("Обрабатываю документ...")
    
    try:
        doc_file = await context.bot.get_file(update.message.document.file_id)
        
        file_name = update.message.document.file_name
        if not file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
            await update.message.reply_text("Пожалуйста, отправьте изображение в формате PNG, JPG, JPEG, BMP или TIFF.")
            await processing_message.delete()
            return
        
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}{os.path.splitext(file_name)[1]}")
        
        await doc_file.download_to_drive(temp_file_path)
        
        text_list, full_text, details = process_image_detailed(temp_file_path)
        
        if text_list:
            response_text = f"Распознанный текст:\n\n{full_text}"
        else:
            response_text = "Не удалось распознать текст на изображении."
        
        await update.message.reply_text(response_text)
        
        await processing_message.delete()
        
    except Exception as e:
        logger.error(f"Error processing Telegram document: {str(e)}")
        await update.message.reply_text(f"Произошла ошибка при обработке документа: {str(e)}")
        await processing_message.delete()
    
    finally:
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            os.rmdir(temp_dir)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Отправьте мне изображение с текстом, и я распознаю его для вас."
    )

@app.post(
    "/ocr/file", 
    response_model=OCRResult,
    summary="Распознавание текста из файла",
    description="Загрузите изображение для распознавания текста с помощью EasyOCR",
    response_description="Возвращает список распознанных текстовых строк",
    tags=["OCR"]
)
async def ocr_from_file(file: UploadFile = File(..., description="Файл изображения в формате JPG, PNG, BMP и т.д.")):
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}.png")
    
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        results = process_image(temp_file_path)
        
        return {"text": results}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки файла: {str(e)}")
    
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)

@app.post(
    "/ocr/file/detailed", 
    response_model=OCRDetailedResult,
    summary="Детальное распознавание текста из файла",
    description="Загрузите изображение для распознавания текста с сохранением структуры",
    response_description="Возвращает расширенную информацию о распознанном тексте с форматированием",
    tags=["OCR"]
)
async def ocr_from_file_detailed(file: UploadFile = File(..., description="Файл изображения в формате JPG, PNG, BMP и т.д.")):
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}.png")
    
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        text_list, full_text, details = process_image_detailed(temp_file_path)
        
        return {"text": text_list, "full_text": full_text, "details": details}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки файла: {str(e)}")
    
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)

@app.post(
    "/ocr/base64", 
    response_model=OCRResult,
    summary="Распознавание текста из base64 изображения",
    description="Отправьте изображение в формате base64 для распознавания текста",
    response_description="Возвращает список распознанных текстовых строк",
    tags=["OCR"]
)
async def ocr_from_base64(image_data: Base64Image):
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}.png")
    
    try:
        img_data = base64.b64decode(image_data.base64_image)
        with open(temp_file_path, "wb") as file:
            file.write(img_data)
        
        results = process_image(temp_file_path)
        
        return {"text": results}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)

@app.post(
    "/ocr/base64/detailed", 
    response_model=OCRDetailedResult,
    summary="Детальное распознавание текста из base64 изображения",
    description="Отправьте изображение в формате base64 для детального распознавания текста с сохранением структуры",
    response_description="Возвращает расширенную информацию о распознанном тексте с форматированием",
    tags=["OCR"]
)
@app.options("/ocr/base64/detailed")
async def ocr_from_base64_detailed(image_data: Base64Image):
    print(f"Received base64 request with filename: {image_data.filename}")
    
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}.png")
    
    try:
        try:
            base64_str = image_data.base64_image
            if "," in base64_str:
                base64_str = base64_str.split(",", 1)[1]
            
            padding = len(base64_str) % 4
            if padding:
                base64_str += "=" * (4 - padding)
                
            img_data = base64.b64decode(base64_str)
            print(f"Successfully decoded base64 data of length: {len(img_data)} bytes")
        except Exception as decode_error:
            print(f"Base64 decoding error: {str(decode_error)}")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid base64 data: {str(decode_error)}"
            )
        
        with open(temp_file_path, "wb") as file:
            file.write(img_data)
        
        if not os.path.exists(temp_file_path) or os.path.getsize(temp_file_path) == 0:
            raise HTTPException(
                status_code=500,
                detail="Failed to save image data to temporary file"
            )
            
        print(f"Image saved to temporary file: {temp_file_path}")
        
        text_list, full_text, details = process_image_detailed(temp_file_path)
        
        response_data = convert_numpy_types({
            "text": text_list, 
            "full_text": full_text, 
            "details": details
        })
        
        return JSONResponse(
            content=response_data,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "*"
            },
            media_type="application/json"
        )
    
    except HTTPException as he:
        raise he
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error processing image: {str(e)}\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")
    
    finally:
        try:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except Exception as cleanup_error:
            print(f"Error during cleanup: {str(cleanup_error)}")

def process_image(image_path):
    image = cv2.imread(image_path)
    if image is None:
        raise HTTPException(
            status_code=400, 
            detail="Не удалось прочитать изображение. Пожалуйста, убедитесь, что загружен правильный файл изображения"
        )
    
    try:
        preprocessed_image = preprocess_image(image)
        
        results = reader.readtext(preprocessed_image)
        
        filtered_results = [result for result in results if result[2] > 0.2]
        
        if not filtered_results:
            return ["Текст не обнаружен на изображении"]
        
        text_results = [result[1] for result in filtered_results]
        
        cleaned_results = [clean_text(text) for text in text_results]
        
        final_results = [text for text in cleaned_results if text.strip()]
        
        return final_results
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка распознавания текста: {str(e)}"
        )

def convert_numpy_types(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_types(item) for item in obj)
    else:
        return obj

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyEncoder, self).default(obj)

def process_image_detailed(image_path):
    image = cv2.imread(image_path)
    if image is None:
        raise HTTPException(
            status_code=400, 
            detail="Не удалось прочитать изображение. Пожалуйста, убедитесь, что загружен правильный файл изображения"
        )
    
    try:
        preprocessed_image = preprocess_image(image)
        
        ocr_results = reader.readtext(preprocessed_image)
        
        filtered_results = [result for result in ocr_results if result[2] > 0.2]
        
        if not filtered_results:
            return ["Текст не обнаружен на изображении"], "", []
        
        sorted_results = sort_results_by_position(filtered_results)
        
        grouped_results = group_by_lines(sorted_results)
        
        text_list = []
        for group in grouped_results:
            line = " ".join([clean_text(item[1]) for item in group])
            if line.strip():
                text_list.append(line)
        
        full_text = "\n".join(text_list)
        
        details = []
        for result in sorted_results:
            bbox, text, confidence = result
            python_bbox = [[int(coord) for coord in point] for point in bbox]
            details.append({
                "text": clean_text(text),
                "confidence": float(confidence),
                "bbox": python_bbox
            })
        
        text_list = convert_numpy_types(text_list)
        full_text = convert_numpy_types(full_text)
        details = convert_numpy_types(details)
        
        return text_list, full_text, details
    
    except Exception as e:
        print(f"Error in process_image_detailed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка распознавания текста: {str(e)}"
        )

def preprocess_image(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    denoised = cv2.fastNlMeansDenoising(enhanced, None, 10, 7, 21)
    
    return denoised

def clean_text(text):
    cleaned = ' '.join(text.split())
    
    artifacts = ["[", "]", "{", "}", "~", "|", "^", "*", "+", "="]
    for artifact in artifacts:
        cleaned = cleaned.replace(artifact, "")
    
    cleaned = cleaned.replace("\"", "\"").replace("\'", "'")
    
    return cleaned

def sort_results_by_position(results):
    return sorted(results, key=lambda r: (r[0][0][1], r[0][0][0]))

def group_by_lines(results):
    if not results:
        return []
    
    heights = [
        max(r[0][2][1], r[0][3][1]) - min(r[0][0][1], r[0][1][1])
        for r in results
    ]
    avg_height = sum(heights) / len(heights) if heights else 20
    
    groups = []
    current_group = [results[0]]
    
    for i in range(1, len(results)):
        current_bbox = results[i][0]
        prev_bbox = results[i-1][0]
        
        current_center_y = (current_bbox[0][1] + current_bbox[2][1]) / 2
        prev_center_y = (prev_bbox[0][1] + prev_bbox[2][1]) / 2
        
        if abs(current_center_y - prev_center_y) < avg_height * 0.7:
            current_group.append(results[i])
        else:
            current_group.sort(key=lambda r: r[0][0][0])
            groups.append(current_group)
            current_group = [results[i]]
    
    if current_group:
        current_group.sort(key=lambda r: r[0][0][0])
        groups.append(current_group)
    
    return groups

@app.get(
    "/", 
    summary="Корневой эндпоинт",
    description="Возвращает информацию о API",
    tags=["Информация"]
)
async def root():
    return {
        "message": "OCR API для распознавания текста из изображений",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs - Swagger UI документация",
            "redoc": "/redoc - ReDoc документация",
            "ocr_file": "/ocr/file - Загрузка файла изображения",
            "ocr_base64": "/ocr/base64 - Отправка base64 изображения",
            "ocr_file_detailed": "/ocr/file/detailed - Детальное распознавание из файла",
            "ocr_base64_detailed": "/ocr/base64/detailed - Детальное распознавание из base64"
        },
        "telegram_bot": "Доступен Telegram бот для распознавания текста с изображений"
    }

@app.get(
    "/api-info", 
    summary="Информация о API",
    description="Предоставляет подробную информацию о API и его возможностях",
    tags=["Информация"]
)
async def api_info():
    return {
        "name": "OCR API with Telegram Bot",
        "description": "API для распознавания текста из изображений с помощью EasyOCR",
        "version": "1.0.0",
        "supported_languages": ["ru", "en"],
        "supported_formats": ["jpg", "jpeg", "png", "bmp", "tiff"],
        "endpoints": {
            "file_upload": {
                "url": "/ocr/file",
                "method": "POST",
                "description": "Распознавание текста из загруженного файла"
            },
            "base64": {
                "url": "/ocr/base64",
                "method": "POST",
                "description": "Распознавание текста из base64 изображения"
            },
            "file_upload_detailed": {
                "url": "/ocr/file/detailed",
                "method": "POST",
                "description": "Детальное распознавание текста из файла с сохранением структуры"
            },
            "base64_detailed": {
                "url": "/ocr/base64/detailed",
                "method": "POST",
                "description": "Детальное распознавание текста из base64 с сохранением структуры"
            }
        },
        "telegram_bot": {
            "description": "Telegram бот для распознавания текста с изображений",
            "usage": "Просто отправьте фото боту, и он вернет распознанный текст"
        }
    }

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
        
    openapi_schema = get_openapi(
        title="OCR API with Telegram Bot",
        version="1.0.0",
        description="""
        # OCR API для распознавания текста с Telegram ботом
        
        Это API позволяет распознавать текст с изображений с использованием библиотеки EasyOCR.
        Также доступен Telegram бот для удобного распознавания текста.
        
        ## Возможности
        
        * Загрузка изображения как файла
        * Загрузка изображения в формате base64
        * Поддержка русского и английского языков
        * Сохранение структуры текста с переносами строк
        * Детальная информация о распознанном тексте
        * Telegram бот для распознавания текста с фотографий
        
        ## Использование
        
        Отправьте запрос POST на /ocr/file, /ocr/base64, /ocr/file/detailed или /ocr/base64/detailed с изображением для анализа.
        Или отправьте фотографию Telegram боту.
        """,
        routes=app.routes,
    )
    
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }
    
    openapi_schema["tags"] = [
        {
            "name": "OCR",
            "description": "Операции по распознаванию текста",
        },
        {
            "name": "Информация",
            "description": "Информационные эндпоинты",
        }
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.options("/{full_path:path}")
async def options_route(full_path: str):
    return JSONResponse(
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With"
        }
    )

@app.middleware("http")
async def add_cors_headers(request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
    response.headers["Access-Control-Max-Age"] = "3600"
    return response

async def run_telegram_bot():
    try:
        logger.info(f"Starting Telegram bot with token: {TELEGRAM_BOT_TOKEN[:5]}...[скрыто]")
        
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        logger.info("Registering Telegram handlers...")
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        
        application.add_error_handler(error_handler)
        
        logger.info("Initializing Telegram bot application...")
        await application.initialize()
        logger.info("Starting Telegram bot application...")
        await application.start()
        logger.info("Starting polling for Telegram updates...")
        await application.updater.start_polling(drop_pending_updates=True)
        
        logger.info("✅ Telegram bot started successfully")
        
        try:
            while True:
                await asyncio.sleep(1)
        finally:
            logger.info("Stopping Telegram bot...")
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
    except Exception as e:
        logger.error(f"❌ Failed to start Telegram bot: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

@app.on_event("startup")
async def startup_event():
    logger.info("Starting FastAPI application...")
    
    if TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN" or not TELEGRAM_BOT_TOKEN:
        logger.warning("⚠️ TELEGRAM_BOT_TOKEN is not set! Bot will not work until you set a valid token.")
        logger.warning("Update the TELEGRAM_BOT_TOKEN variable with your actual bot token.")
        return
    
    bot_task = asyncio.create_task(run_telegram_bot())
    
    app.state.bot_task = bot_task
    
    logger.info("✅ FastAPI application with Telegram bot integration started")

if __name__ == "__main__":
    import uvicorn
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("uvicorn")
    logger.setLevel(logging.INFO)
    
    uvicorn.run(app, host="127.0.0.1", port=3000)