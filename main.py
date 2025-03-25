import easyocr
import cv2
import os
import shutil
import uuid
import tempfile

def extract_text_from_image(file_path):
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}.png")
    
    try:
        if not os.path.exists(file_path):
            print(f"Файл не существует: {file_path}")
            return
        
        shutil.copy2(file_path, temp_file_path)
        
        image = cv2.imread(temp_file_path)
        if image is None:
            print(f"Ошибка при чтении изображения: {file_path}")
            return
        
        reader = easyocr.Reader(['ru', 'en'])
        results = reader.readtext(image)
        
        print("Распознанный текст:")
        for result in results:
            text = result[1]
            print(text)
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)

file_path = r"C:\Users\Viktor\Desktop\Снимок экрана 2025-03-25 185439.png"
extract_text_from_image(file_path)