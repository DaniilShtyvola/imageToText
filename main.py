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
from typing import Optional, List, Dict, Any

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
@app.options("/ocr/base64/detailed")  # Handle OPTIONS preflight request
async def ocr_from_base64_detailed(image_data: Base64Image):
    # Add debug logging
    print(f"Received base64 request with filename: {image_data.filename}")
    
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}.png")
    
    try:
        # Safely decode base64 data with error handling
        try:
            # Strip potential prefixes like "data:image/jpeg;base64,"
            base64_str = image_data.base64_image
            if "," in base64_str:
                base64_str = base64_str.split(",", 1)[1]
            
            # Add padding if needed
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
        
        # Write to file
        with open(temp_file_path, "wb") as file:
            file.write(img_data)
        
        # Verify file was written correctly
        if not os.path.exists(temp_file_path) or os.path.getsize(temp_file_path) == 0:
            raise HTTPException(
                status_code=500,
                detail="Failed to save image data to temporary file"
            )
            
        print(f"Image saved to temporary file: {temp_file_path}")
        
        # Process the image
        text_list, full_text, details = process_image_detailed(temp_file_path)
        
        # Convert all data to JSON-serializable Python types
        response_data = convert_numpy_types({
            "text": text_list, 
            "full_text": full_text, 
            "details": details
        })
        
        # Use a custom JSON encoder to handle any remaining NumPy types
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
        # Re-raise HTTP exceptions
        raise he
    except Exception as e:
        # Log the full exception for debugging
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error processing image: {str(e)}\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")
    
    finally:
        # Clean up temporary files
        try:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except Exception as cleanup_error:
            print(f"Error during cleanup: {str(cleanup_error)}")

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