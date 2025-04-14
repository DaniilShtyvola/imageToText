from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends, Query
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
import time
from typing import Optional, List, Dict, Any, Set
from deep_translator import GoogleTranslator
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ocr_api")

app = FastAPI(
    title="OCR API",
    description="API для распознавания текста из изображений с помощью EasyOCR",
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

# Initialize EasyOCR reader with Russian and English languages
reader = easyocr.Reader(['ru', 'en'])

# Инициализация переводчика
translator = GoogleTranslator(source='auto', target='en')

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

class TranslationRequest(BaseModel):
    target_language: str = Field(..., description="Целевой язык перевода (например, 'en', 'ru', 'fr', 'de')")
    
    class Config:
        schema_extra = {
            "example": {
                "target_language": "en"
            }
        }

class TranslationResult(BaseModel):
    original_text: List[str] = Field(..., description="Исходный распознанный текст")
    translated_text: List[str] = Field(..., description="Переведенный текст")
    full_original_text: str = Field(..., description="Полный исходный текст с сохранением переносов строк")
    full_translated_text: str = Field(..., description="Полный переведенный текст с сохранением переносов строк")
    target_language: str = Field(..., description="Целевой язык перевода")
    
    class Config:
        schema_extra = {
            "example": {
                "original_text": ["Пример текста", "Вторая строка"],
                "translated_text": ["Example text", "Second line"],
                "full_original_text": "Пример текста\nВторая строка",
                "full_translated_text": "Example text\nSecond line",
                "target_language": "en"
            }
        }

class OCRSettings(BaseModel):
    """Параметры для настройки OCR распознавания"""
    languages: List[str] = Field(["ru", "en"], description="Список языков для распознавания")
    min_confidence: float = Field(0.2, description="Минимальный уровень уверенности для распознавания (от 0 до 1)")
    use_advanced_preprocessing: bool = Field(True, description="Использовать продвинутую предобработку изображений")
    detect_orientation: bool = Field(True, description="Автоматически определять ориентацию текста")
    
    class Config:
        schema_extra = {
            "example": {
                "languages": ["ru", "en"],
                "min_confidence": 0.3,
                "use_advanced_preprocessing": True,
                "detect_orientation": True
            }
        }

class OCREnhancedResult(OCRDetailedResult):
    """Расширенный результат OCR распознавания с метаданными"""
    processing_time_ms: int = Field(..., description="Время обработки в миллисекундах")
    image_metadata: Dict[str, Any] = Field(..., description="Метаданные изображения")
    settings: OCRSettings = Field(..., description="Использованные настройки распознавания")
    language_detection: Dict[str, float] = Field(..., description="Вероятные языки на изображении")
    
    class Config:
        schema_extra = {
            "example": {
                "text": ["Распознанная строка 1", "Распознанная строка 2"],
                "full_text": "Распознанная строка 1\nРаспознанная строка 2",
                "details": [
                    {"text": "Распознанная строка 1", "confidence": 0.99, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]},
                    {"text": "Распознанная строка 2", "confidence": 0.95, "bbox": [[10, 40], [100, 40], [100, 60], [10, 60]]}
                ],
                "processing_time_ms": 530,
                "image_metadata": {
                    "width": 800,
                    "height": 600,
                    "format": "jpg"
                },
                "settings": {
                    "languages": ["ru", "en"],
                    "min_confidence": 0.2,
                    "use_advanced_preprocessing": True,
                    "detect_orientation": True
                },
                "language_detection": {
                    "ru": 0.85,
                    "en": 0.15
                }
            }
        }

@app.post(
    "/ocr/file", 
    response_model=OCRResult,
    summary="Распознавание текста из файла",
    description="Загрузите изображение для распознавания текста с помощью EasyOCR",
    response_description="Возвращает список распознанных текстовых строк",
    tags=["OCR"]
)
async def ocr_from_file(
    file: UploadFile = File(..., description="Файл изображения в формате JPG, PNG, BMP и т.д."),
    min_confidence: float = Query(0.2, description="Минимальный уровень уверенности (от 0 до 1)"),
    languages: List[str] = Query(["ru", "en"], description="Языки для распознавания")
):
    logger.info(f"Получен запрос на распознавание из файла: {file.filename}")
    start_time = time.time()
    
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}.png")
    
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Создаем настройки
        ocr_settings = OCRSettings(
            languages=languages,
            min_confidence=min_confidence,
            use_advanced_preprocessing=True,
            detect_orientation=True
        )
        
        # Обрабатываем изображение с улучшенным алгоритмом
        text_list, _, _, _ = process_image_enhanced(temp_file_path, ocr_settings)
        
        logger.info(f"Обработка выполнена за {(time.time() - start_time):.2f} сек.")
        return {"text": text_list}
    
    except Exception as e:
        logger.error(f"Ошибка обработки файла: {str(e)}", exc_info=True)
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
async def ocr_from_file_detailed(
    file: UploadFile = File(..., description="Файл изображения в формате JPG, PNG, BMP и т.д."),
    min_confidence: float = Query(0.2, description="Минимальный уровень уверенности (от 0 до 1)"),
    languages: List[str] = Query(["ru", "en"], description="Языки для распознавания")
):
    logger.info(f"Получен запрос на детальное распознавание из файла: {file.filename}")
    start_time = time.time()
    
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}.png")
    
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Создаем настройки OCR
        ocr_settings = OCRSettings(
            languages=languages,
            min_confidence=min_confidence,
            use_advanced_preprocessing=True,
            detect_orientation=True
        )
        
        # Используем улучшенный метод обработки изображения
        text_list, full_text, details, _ = process_image_enhanced(temp_file_path, ocr_settings)
        
        logger.info(f"Детальная обработка выполнена за {(time.time() - start_time):.2f} сек.")
        
        response_data = convert_numpy_types({
            "text": text_list, 
            "full_text": full_text, 
            "details": details
        })
        
        return JSONResponse(content=response_data)
    
    except Exception as e:
        logger.error(f"Ошибка обработки файла: {str(e)}", exc_info=True)
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
async def ocr_from_base64(
    image_data: Base64Image,
    min_confidence: float = Query(0.2, description="Минимальный уровень уверенности (от 0 до 1)"),
    languages: List[str] = Query(["ru", "en"], description="Языки для распознавания")
):
    logger.info(f"Получен запрос на распознавание из base64 изображения")
    start_time = time.time()
    
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}.png")
    
    try:
        # Безопасное декодирование base64
        try:
            base64_str = image_data.base64_image
            if "," in base64_str:
                base64_str = base64_str.split(",", 1)[1]
            
            padding = len(base64_str) % 4
            if padding:
                base64_str += "=" * (4 - padding)
                
            img_data = base64.b64decode(base64_str)
            logger.info(f"Декодировано base64 данных длиной: {len(img_data)} байт")
        except Exception as decode_error:
            logger.error(f"Ошибка декодирования base64: {str(decode_error)}")
            raise HTTPException(
                status_code=400, 
                detail=f"Некорректные данные base64: {str(decode_error)}"
            )
        
        with open(temp_file_path, "wb") as file:
            file.write(img_data)
        
        # Проверяем, корректно ли записан файл
        if not os.path.exists(temp_file_path) or os.path.getsize(temp_file_path) == 0:
            raise HTTPException(
                status_code=500,
                detail="Не удалось сохранить данные изображения во временный файл"
            )
        
        # Создаем настройки OCR
        ocr_settings = OCRSettings(
            languages=languages,
            min_confidence=min_confidence,
            use_advanced_preprocessing=True,
            detect_orientation=True
        )
        
        # Обрабатываем изображение с улучшенным алгоритмом
        text_list, _, _, _ = process_image_enhanced(temp_file_path, ocr_settings)
        
        logger.info(f"Обработка выполнена за {(time.time() - start_time):.2f} сек.")
        return {"text": text_list}
    
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Ошибка обработки изображения: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка обработки изображения: {str(e)}")
    
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
@app.options("/ocr/base64/detailed")  # Handle OPTIONS preflight request
async def ocr_from_base64_detailed(
    image_data: Base64Image,
    min_confidence: float = Query(0.2, description="Минимальный уровень уверенности (от 0 до 1)"),
    languages: List[str] = Query(["ru", "en"], description="Языки для распознавания")
):
    logger.info(f"Получен запрос на детальное распознавание из base64 изображения: {image_data.filename}")
    start_time = time.time()
    
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}.png")
    
    try:
        # Безопасное декодирование base64
        try:
            # Убираем префиксы типа "data:image/jpeg;base64,"
            base64_str = image_data.base64_image
            if "," in base64_str:
                base64_str = base64_str.split(",", 1)[1]
            
            # Добавляем padding если необходимо
            padding = len(base64_str) % 4
            if padding:
                base64_str += "=" * (4 - padding)
                
            img_data = base64.b64decode(base64_str)
            logger.info(f"Успешно декодированы base64 данные длиной: {len(img_data)} байт")
        except Exception as decode_error:
            logger.error(f"Ошибка декодирования base64: {str(decode_error)}")
            raise HTTPException(
                status_code=400, 
                detail=f"Некорректные данные base64: {str(decode_error)}"
            )
        
        # Запись во временный файл
        with open(temp_file_path, "wb") as file:
            file.write(img_data)
        
        # Проверка корректности записи файла
        if not os.path.exists(temp_file_path) or os.path.getsize(temp_file_path) == 0:
            raise HTTPException(
                status_code=500,
                detail="Не удалось сохранить данные изображения во временный файл"
            )
            
        logger.info(f"Изображение сохранено во временный файл: {temp_file_path}")
        
        # Создаем настройки OCR
        ocr_settings = OCRSettings(
            languages=languages,
            min_confidence=min_confidence,
            use_advanced_preprocessing=True,
            detect_orientation=True
        )
        
        # Обработка изображения с использованием улучшенного алгоритма
        text_list, full_text, details, _ = process_image_enhanced(temp_file_path, ocr_settings)
        
        logger.info(f"Детальная обработка base64 выполнена за {(time.time() - start_time):.2f} сек.")
        
        # Конвертируем все данные в JSON-сериализуемые типы Python
        response_data = convert_numpy_types({
            "text": text_list, 
            "full_text": full_text, 
            "details": details
        })
        
        # Используем пользовательский JSON-энкодер для обработки оставшихся типов NumPy
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
        # Пробрасываем HTTP-исключения
        raise he
    except Exception as e:
        # Логируем полное исключение для отладки
        logger.error(f"Ошибка обработки изображения: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка обработки изображения: {str(e)}")
    
    finally:
        # Очищаем временные файлы
        try:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except Exception as cleanup_error:
            logger.error(f"Ошибка при очистке временных файлов: {str(cleanup_error)}")

@app.post(
    "/ocr/translate/file", 
    response_model=TranslationResult,
    summary="Распознавание и перевод текста из файла",
    description="Загрузите изображение для распознавания и последующего перевода текста",
    response_description="Возвращает оригинальный и переведенный текст с сохранением структуры",
    tags=["Translation"]
)
async def translate_from_file(
    file: UploadFile = File(..., description="Файл изображения в формате JPG, PNG, BMP и т.д."),
    translation_request: TranslationRequest = Depends()
):
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}.png")
    
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Распознаем текст с деталями
        text_list, full_text, details = process_image_detailed(temp_file_path)
        
        # Переводим текст
        translated_texts = translate_text_list(text_list, translation_request.target_language)
        full_translated_text = "\n".join(translated_texts)
        
        return {
            "original_text": text_list,
            "translated_text": translated_texts,
            "full_original_text": full_text,
            "full_translated_text": full_translated_text,
            "target_language": translation_request.target_language
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки файла: {str(e)}")
    
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)

@app.post(
    "/ocr/translate/base64", 
    response_model=TranslationResult,
    summary="Распознавание и перевод текста из base64 изображения",
    description="Отправьте изображение в формате base64 для распознавания и перевода текста",
    response_description="Возвращает оригинальный и переведенный текст с сохранением структуры",
    tags=["Translation"]
)
async def translate_from_base64(
    image_data: Base64Image,
    translation_request: TranslationRequest
):
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}.png")
    
    try:
        # Декодируем base64
        try:
            base64_str = image_data.base64_image
            if "," in base64_str:
                base64_str = base64_str.split(",", 1)[1]
            
            padding = len(base64_str) % 4
            if padding:
                base64_str += "=" * (4 - padding)
                
            img_data = base64.b64decode(base64_str)
        except Exception as decode_error:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid base64 data: {str(decode_error)}"
            )
        
        with open(temp_file_path, "wb") as file:
            file.write(img_data)
        
        # Распознаем текст с деталями
        text_list, full_text, details = process_image_detailed(temp_file_path)
        
        # Переводим текст
        translated_texts = translate_text_list(text_list, translation_request.target_language)
        full_translated_text = "\n".join(translated_texts)
        
        # Подготовка ответа с конвертацией типов
        response_data = convert_numpy_types({
            "original_text": text_list,
            "translated_text": translated_texts,
            "full_original_text": full_text,
            "full_translated_text": full_translated_text,
            "target_language": translation_request.target_language
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
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)

@app.post(
    "/ocr/file/enhanced", 
    response_model=OCREnhancedResult,
    summary="Улучшенное распознавание текста из файла",
    description="Загрузите изображение для распознавания текста с расширенными настройками и метаданными",
    response_description="Возвращает детальную информацию о распознанном тексте с дополнительными метаданными",
    tags=["OCR"]
)
async def ocr_from_file_enhanced(
    file: UploadFile = File(..., description="Файл изображения в формате JPG, PNG, BMP и т.д."),
    min_confidence: float = Query(0.2, description="Минимальный уровень уверенности (от 0 до 1)"),
    use_advanced_preprocessing: bool = Query(True, description="Использовать продвинутую предобработку изображения"),
    detect_orientation: bool = Query(True, description="Автоматически определять ориентацию текста"),
    languages: List[str] = Query(["ru", "en"], description="Языки для распознавания")
):
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}.png")
    
    start_time = time.time()
    
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Создаем настройки OCR
        ocr_settings = OCRSettings(
            languages=languages,
            min_confidence=min_confidence,
            use_advanced_preprocessing=use_advanced_preprocessing,
            detect_orientation=detect_orientation
        )
        
        # Получаем информацию о изображении
        img = cv2.imread(temp_file_path)
        if img is None:
            raise HTTPException(status_code=400, detail="Не удалось прочитать изображение")
        
        height, width = img.shape[:2]
        image_size = os.path.getsize(temp_file_path)
        file_extension = os.path.splitext(file.filename)[1][1:] if file.filename else "unknown"
        
        image_metadata = {
            "width": width,
            "height": height,
            "size_bytes": image_size,
            "format": file_extension,
            "aspect_ratio": round(width / height, 2) if height > 0 else 0
        }
        
        # Обработка и распознавание с учетом настроек
        text_list, full_text, details, language_detection = process_image_enhanced(
            temp_file_path, 
            ocr_settings
        )
        
        # Вычисляем время обработки
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Формируем ответ
        response_data = convert_numpy_types({
            "text": text_list,
            "full_text": full_text,
            "details": details,
            "processing_time_ms": processing_time_ms,
            "image_metadata": image_metadata,
            "settings": ocr_settings.dict(),
            "language_detection": language_detection
        })
        
        return JSONResponse(content=response_data)
    
    except Exception as e:
        logger.error(f"Ошибка обработки файла: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка обработки файла: {str(e)}")
    
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)

@app.post(
    "/ocr/base64/enhanced", 
    response_model=OCREnhancedResult,
    summary="Улучшенное распознавание текста из base64 изображения",
    description="Отправьте изображение в формате base64 для расширенного распознавания текста с настройками",
    response_description="Возвращает детальную информацию о распознанном тексте с дополнительными метаданными",
    tags=["OCR"]
)
async def ocr_from_base64_enhanced(
    image_data: Base64Image,
    min_confidence: float = Query(0.2, description="Минимальный уровень уверенности (от 0 до 1)"),
    use_advanced_preprocessing: bool = Query(True, description="Использовать продвинутую предобработку изображения"),
    detect_orientation: bool = Query(True, description="Автоматически определять ориентацию текста"),
    languages: List[str] = Query(["ru", "en"], description="Языки для распознавания")
):
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}.png")
    
    start_time = time.time()
    
    try:
        # Декодируем base64
        try:
            base64_str = image_data.base64_image
            if "," in base64_str:
                base64_str = base64_str.split(",", 1)[1]
            
            padding = len(base64_str) % 4
            if padding:
                base64_str += "=" * (4 - padding)
                
            img_data = base64.b64decode(base64_str)
            logger.info(f"Successfully decoded base64 data of length: {len(img_data)} bytes")
        except Exception as decode_error:
            logger.error(f"Base64 decoding error: {str(decode_error)}")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid base64 data: {str(decode_error)}"
            )
        
        with open(temp_file_path, "wb") as file:
            file.write(img_data)
        
        # Создаем настройки OCR
        ocr_settings = OCRSettings(
            languages=languages,
            min_confidence=min_confidence,
            use_advanced_preprocessing=use_advanced_preprocessing,
            detect_orientation=detect_orientation
        )
        
        # Получаем информацию о изображении
        img = cv2.imread(temp_file_path)
        if img is None:
            raise HTTPException(status_code=400, detail="Не удалось прочитать изображение")
        
        height, width = img.shape[:2]
        image_size = os.path.getsize(temp_file_path)
        file_extension = os.path.splitext(image_data.filename)[1][1:] if image_data.filename else "unknown"
        
        image_metadata = {
            "width": width,
            "height": height,
            "size_bytes": image_size,
            "format": file_extension,
            "aspect_ratio": round(width / height, 2) if height > 0 else 0
        }
        
        # Обработка и распознавание с учетом настроек
        text_list, full_text, details, language_detection = process_image_enhanced(
            temp_file_path, 
            ocr_settings
        )
        
        # Вычисляем время обработки
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Формируем ответ
        response_data = convert_numpy_types({
            "text": text_list,
            "full_text": full_text,
            "details": details,
            "processing_time_ms": processing_time_ms,
            "image_metadata": image_metadata,
            "settings": ocr_settings.dict(),
            "language_detection": language_detection
        })
        
        return JSONResponse(
            content=response_data,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "*"
            }
        )
    
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")
    
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)

@app.post(
    "/ocr/simple", 
    response_model=OCRResult,
    summary="Простое распознавание текста с изображения",
    description="Загрузите изображение для распознавания текста без сложных настроек",
    response_description="Возвращает список распознанных текстовых строк",
    tags=["OCR Простой"]
)
async def ocr_simple(
    file: UploadFile = File(..., description="Файл изображения в формате JPG, PNG, BMP и т.д."),
    languages: List[str] = Query(["ru", "en"], description="Языки для распознавания")
):
    logger.info(f"Получен запрос на простое распознавание из файла: {file.filename}")
    
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}.png")
    
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Используем базовое распознавание текста
        image = cv2.imread(temp_file_path)
        if image is None:
            raise HTTPException(
                status_code=400, 
                detail="Не удалось прочитать изображение. Пожалуйста, убедитесь, что загружен правильный файл."
            )
        
        # Создаем ридер с указанными языками
        dynamic_reader = easyocr.Reader(languages)
        
        # Базовая предобработка изображения (обычная конвертация в оттенки серого)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Распознаем текст
        results = dynamic_reader.readtext(gray)
        
        # Отфильтровываем результаты с очень низкой уверенностью
        filtered_results = [result for result in results if result[2] > 0.2]
        
        if not filtered_results:
            return {"text": ["Текст не обнаружен на изображении"]}
        
        # Сортируем по позиции
        sorted_results = sort_results_by_position(filtered_results)
        
        # Группировка по строкам
        grouped_results = group_by_lines(sorted_results)
        
        # Формирование списка текстовых строк
        text_list = []
        for group in grouped_results:
            line = " ".join([clean_text(item[1]) for item in group])
            if line.strip():
                text_list.append(line)
        
        return {"text": text_list}
    
    except Exception as e:
        logger.error(f"Ошибка обработки файла: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка обработки файла: {str(e)}")
    
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)

@app.post(
    "/ocr/simple/translate", 
    response_model=TranslationResult,
    summary="Простое распознавание и перевод текста",
    description="Загрузите изображение для распознавания и перевода текста через простой интерфейс",
    response_description="Возвращает распознанный и переведенный текст",
    tags=["OCR Простой"]
)
async def ocr_simple_translate(
    file: UploadFile = File(..., description="Файл изображения в формате JPG, PNG, BMP и т.д."),
    target_language: str = Query("en", description="Язык перевода (например, 'en', 'ru', 'fr')"),
    languages: List[str] = Query(["ru", "en"], description="Языки для распознавания")
):
    logger.info(f"Получен запрос на распознавание и перевод из файла: {file.filename}")
    
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}.png")
    
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Используем базовое распознавание текста
        image = cv2.imread(temp_file_path)
        if image is None:
            raise HTTPException(
                status_code=400, 
                detail="Не удалось прочитать изображение. Пожалуйста, убедитесь, что загружен правильный файл."
            )
        
        # Создаем ридер с указанными языками
        dynamic_reader = easyocr.Reader(languages)
        
        # Базовая предобработка изображения (конвертация в оттенки серого)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Распознаем текст
        results = dynamic_reader.readtext(gray)
        
        # Отфильтровываем результаты с очень низкой уверенностью
        filtered_results = [result for result in results if result[2] > 0.2]
        
        if not filtered_results:
            return {
                "original_text": ["Текст не обнаружен на изображении"],
                "translated_text": ["Text not detected in the image"],
                "full_original_text": "Текст не обнаружен на изображении",
                "full_translated_text": "Text not detected in the image",
                "target_language": target_language
            }
        
        # Сортируем по позиции
        sorted_results = sort_results_by_position(filtered_results)
        
        # Группировка по строкам
        grouped_results = group_by_lines(sorted_results)
        
        # Формирование списка текстовых строк
        text_list = []
        for group in grouped_results:
            line = " ".join([clean_text(item[1]) for item in group])
            if line.strip():
                text_list.append(line)
        
        # Формирование полного текста с переносами строк
        full_text = "\n".join(text_list)
        
        # Переводим текст
        translated_texts = translate_text_list(text_list, target_language)
        full_translated_text = "\n".join(translated_texts)
        
        return {
            "original_text": text_list,
            "translated_text": translated_texts,
            "full_original_text": full_text,
            "full_translated_text": full_translated_text,
            "target_language": target_language
        }
    
    except Exception as e:
        logger.error(f"Ошибка обработки файла: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка обработки файла: {str(e)}")
    
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)

@app.post(
    "/ocr/simple/base64", 
    response_model=OCRResult,
    summary="Простое распознавание текста из base64 изображения",
    description="Отправьте изображение в формате base64 для простого распознавания текста",
    response_description="Возвращает список распознанных текстовых строк",
    tags=["OCR Простой"]
)
async def ocr_simple_base64(
    image_data: Base64Image,
    languages: List[str] = Query(["ru", "en"], description="Языки для распознавания")
):
    logger.info(f"Получен запрос на простое распознавание из base64 изображения")
    
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}.png")
    
    try:
        # Безопасное декодирование base64
        try:
            base64_str = image_data.base64_image
            if "," in base64_str:
                base64_str = base64_str.split(",", 1)[1]
            
            padding = len(base64_str) % 4
            if padding:
                base64_str += "=" * (4 - padding)
                
            img_data = base64.b64decode(base64_str)
            logger.info(f"Декодировано base64 данных длиной: {len(img_data)} байт")
        except Exception as decode_error:
            logger.error(f"Ошибка декодирования base64: {str(decode_error)}")
            raise HTTPException(
                status_code=400, 
                detail=f"Некорректные данные base64: {str(decode_error)}"
            )
        
        with open(temp_file_path, "wb") as file:
            file.write(img_data)
        
        # Проверяем, корректно ли записан файл
        if not os.path.exists(temp_file_path) or os.path.getsize(temp_file_path) == 0:
            raise HTTPException(
                status_code=500,
                detail="Не удалось сохранить данные изображения во временный файл"
            )
        
        # Используем базовое распознавание текста
        image = cv2.imread(temp_file_path)
        if image is None:
            raise HTTPException(
                status_code=400, 
                detail="Не удалось прочитать изображение. Пожалуйста, убедитесь, что загружены корректные данные."
            )
        
        # Создаем ридер с указанными языками
        dynamic_reader = easyocr.Reader(languages)
        
        # Базовая предобработка изображения (обычная конвертация в оттенки серого)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Распознаем текст
        results = dynamic_reader.readtext(gray)
        
        # Отфильтровываем результаты с очень низкой уверенностью
        filtered_results = [result for result in results if result[2] > 0.2]
        
        if not filtered_results:
            return {"text": ["Текст не обнаружен на изображении"]}
        
        # Сортируем по позиции
        sorted_results = sort_results_by_position(filtered_results)
        
        # Группировка по строкам
        grouped_results = group_by_lines(sorted_results)
        
        # Формирование списка текстовых строк
        text_list = []
        for group in grouped_results:
            line = " ".join([clean_text(item[1]) for item in group])
            if line.strip():
                text_list.append(line)
        
        return {"text": text_list}
    
    except Exception as e:
        logger.error(f"Ошибка обработки файла: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка обработки файла: {str(e)}")
    
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)

@app.post(
    "/ocr/simple/translate/base64", 
    response_model=TranslationResult,
    summary="Простое распознавание и перевод текста из base64 изображения",
    description="Отправьте изображение в формате base64 для распознавания и перевода текста",
    response_description="Возвращает распознанный и переведенный текст",
    tags=["OCR Простой"]
)
async def ocr_simple_translate_base64(
    image_data: Base64Image,
    target_language: str = Query("en", description="Язык перевода (например, 'en', 'ru', 'fr')"),
    languages: List[str] = Query(["ru", "en"], description="Языки для распознавания")
):
    logger.info(f"Получен запрос на распознавание и перевод из base64 изображения")
    
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}.png")
    
    try:
        # Безопасное декодирование base64
        try:
            base64_str = image_data.base64_image
            if "," in base64_str:
                base64_str = base64_str.split(",", 1)[1]
            
            padding = len(base64_str) % 4
            if padding:
                base64_str += "=" * (4 - padding)
                
            img_data = base64.b64decode(base64_str)
            logger.info(f"Декодировано base64 данных длиной: {len(img_data)} байт")
        except Exception as decode_error:
            logger.error(f"Ошибка декодирования base64: {str(decode_error)}")
            raise HTTPException(
                status_code=400, 
                detail=f"Некорректные данные base64: {str(decode_error)}"
            )
        
        with open(temp_file_path, "wb") as file:
            file.write(img_data)
        
        # Проверяем, корректно ли записан файл
        if not os.path.exists(temp_file_path) or os.path.getsize(temp_file_path) == 0:
            raise HTTPException(
                status_code=500,
                detail="Не удалось сохранить данные изображения во временный файл"
            )
        
        # Используем базовое распознавание текста
        image = cv2.imread(temp_file_path)
        if image is None:
            raise HTTPException(
                status_code=400, 
                detail="Не удалось прочитать изображение. Пожалуйста, убедитесь, что загружены корректные данные."
            )
        
        # Создаем ридер с указанными языками
        dynamic_reader = easyocr.Reader(languages)
        
        # Базовая предобработка изображения (конвертация в оттенки серого)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Распознаем текст
        results = dynamic_reader.readtext(gray)
        
        # Отфильтровываем результаты с очень низкой уверенностью
        filtered_results = [result for result in results if result[2] > 0.2]
        
        if not filtered_results:
            return {
                "original_text": ["Текст не обнаружен на изображении"],
                "translated_text": ["Text not detected in the image"],
                "full_original_text": "Текст не обнаружен на изображении",
                "full_translated_text": "Text not detected in the image",
                "target_language": target_language
            }
        
        # Сортируем по позиции
        sorted_results = sort_results_by_position(filtered_results)
        
        # Группировка по строкам
        grouped_results = group_by_lines(sorted_results)
        
        # Формирование списка текстовых строк
        text_list = []
        for group in grouped_results:
            line = " ".join([clean_text(item[1]) for item in group])
            if line.strip():
                text_list.append(line)
        
        # Формирование полного текста с переносами строк
        full_text = "\n".join(text_list)
        
        # Переводим текст
        translated_texts = translate_text_list(text_list, target_language)
        full_translated_text = "\n".join(translated_texts)
        
        return {
            "original_text": text_list,
            "translated_text": translated_texts,
            "full_original_text": full_text,
            "full_translated_text": full_translated_text,
            "target_language": target_language
        }
    
    except Exception as e:
        logger.error(f"Ошибка обработки файла: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка обработки файла: {str(e)}")
    
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)

def translate_text_list(text_list, target_language):
    """
    Переводит список текстовых строк на указанный язык используя Google Translate.
    
    Args:
        text_list (List[str]): Список строк для перевода
        target_language (str): Код целевого языка (например, 'en', 'ru', 'fr')
        
    Returns:
        List[str]: Список переведенных строк
    """
    if not text_list:
        return []
    
    try:
        # Устанавливаем переводчик для целевого языка
        translator = GoogleTranslator(source='auto', target=target_language)
        
        # Ограничиваем количество строк для перевода за один запрос
        batch_size = 10
        translated_texts = []
        
        for i in range(0, len(text_list), batch_size):
            batch = text_list[i:i+batch_size]
            
            # Переводим партию текстов
            translations = []
            for text in batch:
                if not text.strip():
                    translations.append("")
                    continue
                    
                # Используем deep-translator для перевода
                translation = translator.translate(text)
                translations.append(translation)
            
            translated_texts.extend(translations)
        
        return translated_texts
    
    except Exception as e:
        print(f"Translation error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка перевода: {str(e)}"
        )

def process_image(image_path):
    """
    Обрабатывает изображение и возвращает список распознанных текстовых строк.
    """
    image = cv2.imread(image_path)
    if image is None:
        raise HTTPException(
            status_code=400, 
            detail="Не удалось прочитать изображение. Пожалуйста, убедитесь, что загружен правильный файл изображения"
        )
    
    try:
        # Применяем предобработку изображения для улучшения распознавания
        preprocessed_image = preprocess_image(image)
        
        # Распознаем текст
        results = reader.readtext(preprocessed_image)
        
        # Отфильтровываем результаты с низкой уверенностью
        filtered_results = [result for result in results if result[2] > 0.2]
        
        if not filtered_results:
            return ["Текст не обнаружен на изображении"]
        
        # Извлекаем текст из результатов
        text_results = [result[1] for result in filtered_results]
        
        # Очищаем текст
        cleaned_results = [clean_text(text) for text in text_results]
        
        # Удаляем пустые строки
        final_results = [text for text in cleaned_results if text.strip()]
        
        return final_results
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка распознавания текста: {str(e)}"
        )

# Add a helper function to convert NumPy types to Python native types
def convert_numpy_types(obj):
    """
    Recursively converts NumPy types to Python native types to make them JSON serializable.
    """
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

# Custom JSON encoder that handles NumPy types
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
    """
    Обрабатывает изображение и возвращает детальную информацию о распознанном тексте
    с сохранением структуры и форматирования.
    """
    image = cv2.imread(image_path)
    if image is None:
        raise HTTPException(
            status_code=400, 
            detail="Не удалось прочитать изображение. Пожалуйста, убедитесь, что загружен правильный файл изображения"
        )
    
    try:
        # Предобработка изображения
        preprocessed_image = preprocess_image(image)
        
        # Распознавание текста с сохранением координат
        ocr_results = reader.readtext(preprocessed_image)
        
        # Фильтрация результатов с низкой уверенностью
        filtered_results = [result for result in ocr_results if result[2] > 0.2]
        
        if not filtered_results:
            return ["Текст не обнаружен на изображении"], "", []
        
        # Сортировка результатов по вертикальной позиции для сохранения структуры строк
        sorted_results = sort_results_by_position(filtered_results)
        
        # Группировка текста по строкам на основе вертикального положения
        grouped_results = group_by_lines(sorted_results)
        
        # Формирование списка текстовых строк
        text_list = []
        for group in grouped_results:
            line = " ".join([clean_text(item[1]) for item in group])
            if line.strip():
                text_list.append(line)
        
        # Формирование полного текста с переносами строк
        full_text = "\n".join(text_list)
        
        # Подготовка детальной информации
        details = []
        for result in sorted_results:
            bbox, text, confidence = result
            # Convert NumPy array to regular Python list
            python_bbox = [[int(coord) for coord in point] for point in bbox]
            details.append({
                "text": clean_text(text),
                "confidence": float(confidence),  # Ensure float, not numpy.float
                "bbox": python_bbox
            })
        
        # Convert all results to Python native types to ensure JSON serialization
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
    """
    Предобработка изображения для улучшения результатов OCR.
    """
    # Конвертация в оттенки серого
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Бинаризация с адаптивным порогом
    # Это помогает подчеркнуть текст на изображениях с переменной яркостью
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    
    # Улучшение контраста
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    # Удаление шума
    denoised = cv2.fastNlMeansDenoising(enhanced, None, 10, 7, 21)
    
    return denoised

def clean_text(text):
    """
    Очищает и нормализует распознанный текст.
    """
    # Удаление лишних пробелов
    cleaned = ' '.join(text.split())
    
    # Убираем некоторые артефакты, которые могут появиться при OCR
    artifacts = ["[", "]", "{", "}", "~", "|", "^", "*", "+", "="]
    for artifact in artifacts:
        cleaned = cleaned.replace(artifact, "")
    
    # Нормализация кавычек
    cleaned = cleaned.replace("\"", "\"").replace("\'", "'")
    
    return cleaned

def sort_results_by_position(results):
    """
    Сортирует результаты OCR по их позиции на изображении (сверху вниз, слева направо).
    """
    # Сортировка по вертикальной позиции (y-координата верхней левой точки)
    return sorted(results, key=lambda r: (r[0][0][1], r[0][0][0]))

def group_by_lines(results):
    """
    Группирует распознанные тексты по строкам на основе их вертикального положения.
    """
    if not results:
        return []
    
    # Определение средней высоты строки
    heights = [
        max(r[0][2][1], r[0][3][1]) - min(r[0][0][1], r[0][1][1])
        for r in results
    ]
    avg_height = sum(heights) / len(heights) if heights else 20
    
    # Группировка по строкам
    groups = []
    current_group = [results[0]]
    
    for i in range(1, len(results)):
        current_bbox = results[i][0]
        prev_bbox = results[i-1][0]
        
        # Центры по Y
        current_center_y = (current_bbox[0][1] + current_bbox[2][1]) / 2
        prev_center_y = (prev_bbox[0][1] + prev_bbox[2][1]) / 2
        
        # Если вертикальная разница меньше половины средней высоты строки,
        # считаем, что это та же строка
        if abs(current_center_y - prev_center_y) < avg_height * 0.7:
            current_group.append(results[i])
        else:
            # Сортируем группу по горизонтальной позиции
            current_group.sort(key=lambda r: r[0][0][0])
            groups.append(current_group)
            current_group = [results[i]]
    
    # Добавляем последнюю группу
    if current_group:
        current_group.sort(key=lambda r: r[0][0][0])
        groups.append(current_group)
    
    return groups

def advanced_image_preprocessing(image, settings: OCRSettings):
    """
    Продвинутая предобработка изображения для улучшения точности OCR с применением
    различных алгоритмов улучшения изображения.
    
    Args:
        image: Исходное изображение в формате OpenCV
        settings: Настройки предобработки
        
    Returns:
        Предобработанное изображение
    """
    # Шаг 1: Преобразование в оттенки серого
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # Шаг 2: Применение различных методов улучшения
    # Масштабирование для улучшения разрешения текста
    scale_factor = 1.5
    height, width = gray.shape[:2]
    scaled = cv2.resize(gray, (int(width * scale_factor), int(height * scale_factor)), 
                       interpolation=cv2.INTER_CUBIC)
    
    # Удаление шума с помощью двустороннего фильтра
    # Сохраняет края текста, но удаляет шум
    denoised = cv2.bilateralFilter(scaled, 9, 75, 75)
    
    # Улучшение контраста с CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    
    # Шаг 3: Адаптивная бинаризация для выделения текста
    # Особенно полезно для документов с неравномерным освещением
    binary = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 15, 8
    )
    
    # Шаг 4: Морфологические операции для очистки текста
    # Создание структурирующего элемента
    kernel = np.ones((1, 1), np.uint8)
    
    # Операция морфологического открытия (эрозия с последующей дилатацией)
    # Удаляет мелкие шумы и сглаживает контуры
    opening = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    
    # Операция закрытия для заполнения пробелов внутри символов
    closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel)
    
    # Шаг 5: Настройка ориентации (опционально)
    if settings.detect_orientation:
        # Здесь можно добавить код для определения и коррекции ориентации
        # Например, с использованием преобразования Хафа для поиска линий текста
        # Для простоты этот шаг опустим
        pass
    
    return closing

def process_image_enhanced(image_path, settings: OCRSettings):
    """
    Улучшенная обработка изображения с расширенными параметрами и возвращением
    детальных результатов OCR.
    
    Args:
        image_path: Путь к изображению
        settings: Настройки OCR
    
    Returns:
        Кортеж (список текста, полный текст, детали, определенные языки)
    """
    # Загрузка изображения
    image = cv2.imread(image_path)
    if image is None:
        raise HTTPException(
            status_code=400, 
            detail="Не удалось прочитать изображение. Проверьте формат файла."
        )
    
    try:
        # Инициализация динамического ридера для указанных языков
        dynamic_reader = easyocr.Reader(settings.languages)
        
        # Предобработка изображения
        if settings.use_advanced_preprocessing:
            preprocessed_image = advanced_image_preprocessing(image, settings)
        else:
            preprocessed_image = preprocess_image(image)
        
        # Распознавание текста
        logger.info(f"Starting OCR with languages: {settings.languages}")
        ocr_results = dynamic_reader.readtext(preprocessed_image)
        
        # Фильтрация результатов по уровню уверенности
        filtered_results = [result for result in ocr_results if result[2] > settings.min_confidence]
        
        if not filtered_results:
            # Возвращаем пустые результаты
            language_detection = {lang: 0.0 for lang in settings.languages}
            language_detection[settings.languages[0]] = 1.0  # По умолчанию первый язык
            return ["Текст не обнаружен"], "", [], language_detection
        
        # Сортировка по позиции
        sorted_results = sort_results_by_position(filtered_results)
        
        # Группировка по строкам
        grouped_results = group_by_lines(sorted_results)
        
        # Формирование списка текстовых строк
        text_list = []
        for group in grouped_results:
            line = " ".join([clean_text(item[1]) for item in group])
            if line.strip():
                text_list.append(line)
        
        # Формирование полного текста
        full_text = "\n".join(text_list)
        
        # Подготовка детальной информации
        details = []
        confidence_sum = 0
        for result in sorted_results:
            bbox, text, confidence = result
            confidence_sum += confidence
            python_bbox = [[int(coord) for coord in point] for point in bbox]
            details.append({
                "text": clean_text(text),
                "confidence": float(confidence),
                "bbox": python_bbox
            })
        
        # Определение вероятного языка
        language_detection = estimate_languages(text_list, settings.languages)
        
        # Преобразование к Python-типам
        text_list = convert_numpy_types(text_list)
        full_text = convert_numpy_types(full_text)
        details = convert_numpy_types(details)
        
        return text_list, full_text, details, language_detection
    
    except Exception as e:
        logger.error(f"Error in enhanced OCR processing: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Ошибка распознавания текста: {str(e)}"
        )

def estimate_languages(text_list, supported_languages):
    """
    Оценивает вероятность языка на основе распознанного текста.
    
    Args:
        text_list: Список распознанных текстовых строк
        supported_languages: Список поддерживаемых языков
        
    Returns:
        Словарь {язык: вероятность} для каждого поддерживаемого языка
    """
    # Здесь можно реализовать более сложную логику определения языка
    # Для простоты используем очень базовый подход на основе частотных характеристик
    
    if not text_list:
        # Если текст не распознан, возвращаем равные вероятности
        return {lang: 1.0/len(supported_languages) for lang in supported_languages}
    
    # Словари характерных букв для разных языков
    language_chars = {
        'ru': set('абвгдеёжзийклмнопрстуфхцчшщъыьэюя'),
        'en': set('abcdefghijklmnopqrstuvwxyz'),
        'fr': set('abcdefghijklmnopqrstuvwxyzàâçéèêëîïôùûüÿ'),
        'de': set('abcdefghijklmnopqrstuvwxyzäöüß'),
        'es': set('abcdefghijklmnopqrstuvwxyzáéíóúüñ'),
        'it': set('abcdefghijklmnopqrstuvwxyzàèéìíîòóùú'),
        'zh': set(),  # Для китайского нужен другой подход
        'ja': set(),  # Для японского нужен другой подход
        'ko': set(),  # Для корейского нужен другой подход
    }
    
    # Подсчет символов для каждого языка
    counts = {lang: 0 for lang in supported_languages}
    total_chars = 0
    
    # Объединяем весь текст и приводим к нижнему регистру
    full_text = ' '.join(text_list).lower()
    
    for char in full_text:
        total_chars += 1
        for lang in supported_languages:
            if lang in language_chars and char in language_chars[lang]:
                counts[lang] += 1
    
    # Вычисляем вероятности
    if total_chars > 0:
        probabilities = {lang: count / total_chars for lang, count in counts.items()}
    else:
        probabilities = {lang: 1.0/len(supported_languages) for lang in supported_languages}
    
    # Нормализация, чтобы сумма всех вероятностей была равна 1
    total_prob = sum(probabilities.values())
    if total_prob > 0:
        normalized_probs = {lang: prob / total_prob for lang, prob in probabilities.items()}
    else:
        normalized_probs = {lang: 1.0/len(supported_languages) for lang in supported_languages}
    
    return normalized_probs

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
        }
    }

@app.get(
    "/api-info", 
    summary="Информация о API",
    description="Предоставляет подробную информацию о API и его возможностях",
    tags=["Информация"]
)
async def api_info():
    return {
        "name": "OCR API",
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
        }
    }

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
        
    openapi_schema = get_openapi(
        title="OCR API",
        version="1.0.0",
        description="""
        # OCR API для распознавания текста
        
        Это API позволяет распознавать текст с изображений с использованием библиотеки EasyOCR.
        
        ## Возможности
        
        * Загрузка изображения как файла
        * Загрузка изображения в формате base64
        * Поддержка русского и английского языков
        * Сохранение структуры текста с переносами строк
        * Детальная информация о распознанном тексте
        
        ## Использование
        
        Отправьте запрос POST на /ocr/file, /ocr/base64, /ocr/file/detailed или /ocr/base64/detailed с изображением для анализа.
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

# Add OPTIONS handler for all routes to support CORS preflight requests
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

# Add a middleware to ensure CORS headers are applied to all responses
@app.middleware("http")
async def add_cors_headers(request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
    response.headers["Access-Control-Max-Age"] = "3600"
    return response

if __name__ == "__main__":
    import uvicorn
    
    # Enable debug logging
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("uvicorn")
    logger.setLevel(logging.INFO)
    
    # Run the server
    uvicorn.run(app, host="127.0.0.1", port=3000)