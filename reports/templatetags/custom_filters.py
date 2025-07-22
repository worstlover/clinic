# reports/templatetags/custom_filters.py

from django import template

register = template.Library()

@register.filter
def jalali_date_format(value):
    """Converts a Gregorian date to Jalali format."""
    # Your logic for converting date to Jalali
    # This is just a placeholder example
    if value:
        from persiantools.jdatetime import JalaliDate
        return JalaliDate(value).strftime('%Y/%m/%d')
    return ""

@register.filter
def my_other_filter(value):
    # Define your other custom filters here
    return f"Processed: {value}"
register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    return dictionary.get(key)