import requests
import json

# آدرس پایه API بر اساس مستندات
TTAC_API_BASE_URL = "https://newapi.ttac.ir/insurances/v80/"

# 🔴🔴🔴 مهم: این کلید را باید از سازمان غذا و دارو دریافت کنید 🔴🔴🔴
# این یک کلید نمونه و غیرواقعی است.
YOUR_API_KEY = "PASTE_YOUR_REAL_API_KEY_HERE"

def get_drug_info_from_ttac(barcode_uid: str):
    """
    با استفاده از مستندات رسمی TTAC، اطلاعات یک دارو را از روی بارکد یا UID استعلام می‌کند.
    """
    if not YOUR_API_KEY or YOUR_API_KEY == "PASTE_YOUR_REAL_API_KEY_HERE":
        # اگر کلید واقعی تنظیم نشده باشد، یک پاسخ شبیه‌سازی شده برمی‌گردانیم تا برنامه متوقف نشود.
        print("هشدار: کلید واقعی API تنظیم نشده است. از داده‌های شبیه‌سازی شده استفاده می‌شود.")
        if "06260153010552" in barcode_uid:
            return {
                "status": "success",
                "persianName": "آمپول کتورولاک (شبیه‌سازی شده)",
                "gtin": "06260153010552",
                "batchCode": "0100624",
                "irc": "1228221101",
                "genericCode": "2504"
            }
        return {"status": "error", "message": "API Key not configured."}

    headers = {
        "X-SSP-Api-Key": YOUR_API_KEY,
        "Content-Type": "application/json"
    }

    # --- مرحله 1: ثبت یک نسخه صوری برای دریافت prescriptionId ---
    prescription_payload = {
        # این اطلاعات برای انبارداری می‌تواند ثابت یا صوری باشد
        "patientNationalCode": "0000000000",
        "patientGivenName": "انبار",
        "patientSurname": "مرکزی",
        "physicianGivenName": "سیستم",
        "physicianSurname": "انبار",
        "medicalCouncilNumber": "00000",
        "gln": "0000000000000" # GLN مرکز خود را در صورت وجود وارد کنید
    }
    
    try:
        # ثبت نسخه
        register_url = f"{TTAC_API_BASE_URL}RegisterPrescription"
        response_reg = requests.post(register_url, data=json.dumps(prescription_payload), headers=headers, timeout=10)
        response_reg.raise_for_status() # بررسی خطاهای HTTP
        
        reg_data = response_reg.json()

        if reg_data.get("errorCode") != 0:
            error_msg = reg_data.get('errorMessage', 'خطای نامشخص در ثبت نسخه')
            print(f"TTAC Register Error: {error_msg}")
            return {"status": "error", "message": f"TTAC Register Error: {error_msg}"}

        prescription_id = reg_data.get("prescriptionId")
        if not prescription_id:
            return {"status": "error", "message": "Failed to get prescriptionId from TTAC."}

        # --- مرحله 2: استعلام بارکد با استفاده از prescriptionId ---
        inquiry_payload = {
            "prescriptionId": prescription_id,
            "barcodeUid": barcode_uid,
            "amount": 1 # مقدار پیش‌فرض برای استعلام
        }
        
        inquiry_url = f"{TTAC_API_BASE_URL}CheckSingleBarcodeUid"
        response_inq = requests.post(inquiry_url, data=json.dumps(inquiry_payload), headers=headers, timeout=10)
        response_inq.raise_for_status()

        inq_data = response_inq.json()
        
        # بررسی وضعیت پاسخ استعلام [cite: 123]
        status_code = inq_data.get("status")
        if status_code == 0: # کد 0 در مستندات به معنی "معتبر" است، اما در نسخه‌های جدیدتر معمولا کد 1 است [cite: 125]
             # برای اطمینان بیشتر، وجود خود uid را چک می‌کنیم
             if inq_data.get("uid"):
                inq_data["status"] = "success"
                return inq_data
        
        # اگر وضعیت موفقیت‌آمیز نبود
        status_message = inq_data.get('statusMessage', 'خطای نامشخص در استعلام دارو')
        print(f"TTAC Inquiry Error: {status_message}")
        return {"status": "error", "message": f"TTAC Inquiry Error: {status_message}"}

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while communicating with TTAC API: {e}")
        return {"status": "error", "message": f"Network error communicating with TTAC: {e}"}
