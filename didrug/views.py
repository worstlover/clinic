# didrug/views.py
import io
import re
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import numpy as np
import cv2
import easyocr

# Initialize OCR reader once for efficiency
try:
    ocr_reader = easyocr.Reader(['fa', 'en'])
except Exception as e:
    print(f"Error initializing EasyOCR: {e}. Please check your internet connection or download models manually.")
    ocr_reader = None

@csrf_exempt
def process_drug_info (request):
    """
    Handles both GET (to render the form) and POST (to process data) requests.
    """
    if request.method == 'GET':
        return render(request, 'didrug/didrug.html')

    elif request.method == 'POST':
        if ocr_reader is None:
            return JsonResponse({'error': 'OCR service is not available. Please check server logs.'}, status=503)

        # Initialize variables to hold results
        persian_name = None
        qr_code_content = None
        expiry_date = None

        try:
            # --- Process Drug Box Image (if available) ---
            if 'drug_box_image' in request.FILES:
                drug_box_file = request.FILES.get('drug_box_image')
                drug_box_image_bytes = drug_box_file.read()
                ocr_results = ocr_reader.readtext(drug_box_image_bytes, detail=0)
                
                # Find the best Persian name
                for text in ocr_results:
                    if re.search(r'[\u0600-\u06FF]', text):
                        persian_name = text
                        break # Take the first detected Persian name

            # --- Process QR Code (from file or live content) ---
            if 'qr_code_image' in request.FILES:
                qr_code_file = request.FILES.get('qr_code_image')
                qr_image_bytes = qr_code_file.read()
                qr_image_np = np.frombuffer(qr_image_bytes, np.uint8)
                qr_image = cv2.imcode(qr_image_np, cv2.IMREAD_COLOR)

                qr_detector = cv2.QRCodeDetector()
                qr_code_content, _, _ = qr_detector.detectAndDecode(qr_image)

            elif 'qr_code_content' in request.POST:
                qr_code_content = request.POST.get('qr_code_content', '')

            if qr_code_content:
                match = re.search(r'17(\d{6})', qr_code_content)
                if match:
                    date_str = match.group(1)
                    year = '20' + date_str[0:2]
                    month = date_str[2:4]
                    day = date_str[4:6]
                    expiry_date = f"{year}/{month}/{day}"

            # --- Final Logic and Response ---
            if persian_name or qr_code_content:
                message = "اطلاعات با موفقیت استخراج شد."
                status = 'success'
                if not persian_name:
                    message = "نام دارو یافت نشد. سایر اطلاعات استخراج شد."
                    status = 'warning'
                if not qr_code_content:
                    message = "کد QR یافت نشد. سایر اطلاعات استخراج شد."
                    status = 'warning'

                return JsonResponse({
                    'status': status,
                    'message': message,
                    'persian_name': persian_name,
                    'qr_code_content': qr_code_content,
                    'expiry_date': expiry_date,
                })
            else:
                return JsonResponse({'status': 'error', 'message': 'هیچ اطلاعاتی برای پردازش یافت نشد.'}, status=400)

        except Exception as e:
            print(f"Error processing data: {e}")
            return JsonResponse({'status': 'error', 'message': 'خطایی در پردازش رخ داد. لطفاً گزارش‌های سرور را بررسی کنید.'}, status=500)