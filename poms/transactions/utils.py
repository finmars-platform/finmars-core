MAX_TEXT = 40
MAX_NUMBER = 40
MAX_DATE = 10


# generate user fields
def generate_user_fields(
    max_text=MAX_TEXT, max_number=MAX_NUMBER, max_date=MAX_DATE
) -> list:
    fields = [f"user_text_{i}" for i in range(1, max_text + 1)]
    fields.extend([f"user_number_{i}" for i in range(1, max_number + 1)])
    fields.extend([f"user_date_{i}" for i in range(1, max_date + 1)])
    return fields
