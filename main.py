from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import easyocr
import cv2
import numpy as np
import base64
import uuid
import tempfile
import os
import shutil
from typing import Optional, List

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

def process_image(image_path):
    image = cv2.imread(image_path)
    if image is None:
        raise HTTPException(
            status_code=400, 
            detail="Не удалось прочитать изображение. Пожалуйста, убедитесь, что загружен правильный файл изображения"
        )
    
    try:
        results = reader.readtext(image)
        text_results = [result[1] for result in results]
        
        if not text_results:
            return ["Текст не обнаружен на изображении"]
        
        return text_results
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка распознавания текста: {str(e)}"
        )

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
            "ocr_base64": "/ocr/base64 - Отправка base64 изображения"
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
        
        ## Использование
        
        Отправьте запрос POST на /ocr/file или /ocr/base64 с изображением для анализа.
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=3000)