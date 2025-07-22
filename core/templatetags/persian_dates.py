# D:\final\core\templatetags\persian_dates.py

from django import template
import jdatetime # برای تبدیل تاریخ شمسی
from datetime import date, datetime # برای اطمینان از اینکه ورودی یک آبجکت تاریخ میلادی است

register = template.Library()

@register.filter
def to_jalali(value, format_string="%Y/%m/%d"):
    """
    Converts a Gregorian date object to a Jalali date string.
    Usage: {{ some_date_field|to_jalali:"%Y/%m/%d" }}
    Default format: Y/m/d (e.g., 1402/03/28)
    """
    if isinstance(value, date): # مطمئن می شویم که ورودی یک آبجکت تاریخ میلادی است (تاریخ یا تاریخ و زمان)
        try:
            # تبدیل تاریخ میلادی به شمسی
            jdate = jdatetime.date.fromgregorian(date=value)
            return jdate.strftime(format_string)
        except Exception:
            # در صورت بروز خطا در تبدیل، رشته خالی یا '-' برمی گرداند
            return "-"
    return "" # اگر ورودی تاریخ نباشد یا None باشد

@register.filter
def to_jalali_datetime(value, format_string="%Y/%m/%d %H:%M"):
    """
    Converts a Gregorian datetime object to a Jalali datetime string.
    Usage: {{ some_datetime_field|to_jalali_datetime:"%Y/%m/%d %H:%M" }}
    Default format: Y/m/d H:M (e.g., 1402/03/28 10:30)
    """
    if isinstance(value, datetime): # مطمئن می شویم که ورودی یک آبجکت datetime میلادی است
        try:
            # تبدیل datetime میلادی به jdatetime شمسی
            jdate = jdatetime.datetime.fromgregorian(datetime=value)
            return jdate.strftime(format_string)
        except Exception:
            return "-"
    return "" # اگر ورودی datetime نباشد یا None باشد