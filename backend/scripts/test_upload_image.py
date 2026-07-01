import io
import requests
from PIL import Image, ImageDraw

def main():
    print("Creating mock image with text...")
    img = Image.new('RGB', (400, 200), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((20, 20), "Jadwal Ujian Semester Ganjil 2025/2026", fill=(0, 0, 0))
    d.text((20, 60), "Kalender Akademik Fakultas Teknik", fill=(0, 0, 0))
    d.text((20, 100), "1. Registrasi KRS: 1-15 Agustus 2025", fill=(0, 0, 0))
    d.text((20, 140), "2. Mulai Kuliah: 1 September 2025", fill=(0, 0, 0))
    
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_bytes = img_byte_arr.getvalue()
    
    print("Logging in to get auth token...")
    login_payload = {"email": "admin@gmail.com", "password": "admin123"}
    resp = requests.post("http://127.0.0.1:3001/api/auth/login", json=login_payload)
    token = resp.json()["access_token"]
    
    print("Uploading image to /api/ingest/file...")
    headers = {"Authorization": f"Bearer {token}"}
    files = {"file": ("test_kalender.png", img_bytes, "image/png")}
    data = {"overwrite_old": "true"}
    
    upload_resp = requests.post("http://127.0.0.1:3001/api/ingest/file", headers=headers, files=files, data=data)
    print("Upload Status:", upload_resp.status_code)
    print("Upload Response:", upload_resp.text)

if __name__ == "__main__":
    main()
