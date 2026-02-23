import sqlite3
import os

def rebuild_tables():
    db_path = 'db.sqlite3'
    if not os.path.exists(db_path):
        print("❌ فایل دیتابیس پیدا نشد!")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("⚠️ در حال پاکسازی جداول قدیمی (برای بازسازی تمیز)...")
        # حذف جداول به ترتیب برای رعایت قیدهای کلید خارجی
        tables_to_drop = [
            'core_dailyreport_requirements',
            'core_requirementview',
            'core_dailyreport',
            'core_requirement'
        ]
        for table in tables_to_drop:
            cursor.execute(f"DROP TABLE IF EXISTS {table};")

        print("🏗️ ۱. ساخت جدول Requirement با فیلد status و admin_note...")
        cursor.execute("""
        CREATE TABLE core_requirement (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(500) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'created',
            is_archived BOOLEAN NOT NULL DEFAULT 0,
            admin_note TEXT,
            created_at DATETIME NOT NULL,
            creator_id INTEGER NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES auth_user (id)
        );
        """)

        print("🏗️ ۲. ساخت جدول RequirementView (واسط بازدید مدیران)...")
        cursor.execute("""
        CREATE TABLE core_requirementview (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            viewed_at DATETIME NOT NULL,
            admin_id INTEGER NOT NULL,
            requirement_id INTEGER NOT NULL,
            FOREIGN KEY (admin_id) REFERENCES auth_user (id),
            FOREIGN KEY (requirement_id) REFERENCES core_requirement (id)
        );
        """)

        print("🏗️ ۳. ساخت جدول DailyReport (نسخه کامل)...")
        cursor.execute("""
        CREATE TABLE core_dailyreport (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            shift_type VARCHAR(20) NOT NULL,
            created_at DATETIME NOT NULL,
            dispatched_action TEXT,
            next_shift_plan TEXT,
            ambulance_status TEXT,
            equipment_status TEXT,
            occupational_health TEXT,
            health_alerts TEXT,
            environmental_inspections TEXT,
            general_notes TEXT,
            outpatient_count INTEGER DEFAULT 0,
            nursing_services_count INTEGER DEFAULT 0,
            visit_exam_count INTEGER DEFAULT 0,
            vaccination_count INTEGER DEFAULT 0,
            consultation_count INTEGER DEFAULT 0,
            referral_to_clinic INTEGER DEFAULT 0,
            doctor_id INTEGER,
            nurse_id INTEGER,
            driver_id INTEGER,
            FOREIGN KEY (doctor_id) REFERENCES auth_user (id),
            FOREIGN KEY (nurse_id) REFERENCES auth_user (id),
            FOREIGN KEY (driver_id) REFERENCES auth_user (id)
        );
        """)

        print("🏗️ ۴. ساخت جدول رابط ManyToMany...")
        cursor.execute("""
        CREATE TABLE core_dailyreport_requirements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dailyreport_id INTEGER NOT NULL,
            requirement_id INTEGER NOT NULL,
            FOREIGN KEY (dailyreport_id) REFERENCES core_dailyreport (id),
            FOREIGN KEY (requirement_id) REFERENCES core_requirement (id)
        );
        """)

        conn.commit()
        conn.close()
        print("\n✅ تبریک! تمام جداول با ستون‌های جدید (status و غیره) ساخته شدند.")

    except sqlite3.OperationalError as e:
        print(f"❌ خطا: دیتابیس قفل است. احتمالا سرور (runserver) باز است. آن را ببندید.\n{e}")

if __name__ == "__main__":
    rebuild_tables()