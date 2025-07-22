# D:\final\core\utils.py

def convert_fa_numbers_to_en(text):
    """
    Converts Persian/Arabic digits in a string to English digits.
    """
    if not isinstance(text, str):
        return text # Return as is if not a string (e.g., None, int)

    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    arabic_digits = '٠١٢٣٤٥٦٧٨٩' # Some keyboards might use Arabic digits
    english_digits = '0123456789'

    translation_table_persian = str.maketrans(persian_digits, english_digits)
    translation_table_arabic = str.maketrans(arabic_digits, english_digits)

    # Apply both translations
    converted_text = text.translate(translation_table_persian)
    converted_text = converted_text.translate(translation_table_arabic)
    
    return converted_text