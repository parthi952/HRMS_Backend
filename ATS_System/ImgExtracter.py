import cv2
import easyocr
import os

reader = easyocr.Reader(['en'])

img_path = r"C:\Users\parth_kozqdcr\OneDrive\Desktop\Hrm_Backend\ATS_System\Document\1.png"

def extract_text_from_image(img_path: str):
    if not os.path.exists(img_path):
        return f"Error: The file '{img_path}' does not exist."
    
    try:

        results = reader.readtext(img_path)
        
        text = "\n".join([res[1] for res in results])
        return text
    except Exception as e:
        return f"Error processing image with EasyOCR: {e}"


if __name__ == "__main__":
    print(extract_text_from_image(img_path))
    