import pdfplumber
import os

File_Path = r"C:\Users\parth_kozqdcr\OneDrive\Desktop\Hrm_Backend\ATS_System\Document\1.pdf"

def extract_text_from_pdf(file_path: str):
    
    if not os.path.exists(file_path):
        return f"Error: The file '{file_path}' does not exist."

    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        return f"Error opening PDF: {e}"

    return text


if __name__ == "__main__":
    print(extract_text_from_pdf(File_Path))
