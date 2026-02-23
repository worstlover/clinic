import sqlite3
import os

db_path = 'db.sqlite3'

def fix_requirement_view_table():
    if not os.path.exists(db_path):
        print("❌ فایل دیتابیس پیدا نشد!")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # اسکریپت ساخت جدول طبق فیلدهای مدل RequirementView شما
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS core_requirementview (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        viewed_at DATETIME NOT NULL,
        admin_id INTEGER NOT NULL,
        requirement_id INTEGER NOT NULL,
        FOREIGN KEY (admin_id) REFERENCES auth_user (id) ON DELETE CASCADE,
        FOREIGN KEY (requirement_id) REFERENCES core_requirement (id) ON DELETE CASCADE,
        UNIQUE (admin_id, requirement_id)
    );
    """

    try:
        print("🛠 در حال ساخت جدول core_requirementview...")
        cursor.execute(create_table_sql)
        
        # ثبت در جدول مائیگریشن‌های جنگو (اختیاری برای جلوگیری از تداخل آینده)
        conn.commit()
        print("✅ جدول با موفقیت ایجاد شد.")
    except sqlite3.OperationalError as e:
        print(f"❌ خطا: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix_requirement_view_table()