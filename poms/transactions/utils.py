import json

MAX_TEXT = 40
MAX_NUMBER = 40
MAX_DATE = 10


# generate user fields
def generate_user_fields(max_text=MAX_TEXT, max_number=MAX_NUMBER, max_date=MAX_DATE) -> list:
    fields = [f"user_text_{i}" for i in range(1, max_text + 1)]
    fields.extend([f"user_number_{i}" for i in range(1, max_number + 1)])
    fields.extend([f"user_date_{i}" for i in range(1, max_date + 1)])
    return fields


def _read_json_text(raw: str):
    if raw is None:
        return None
    # 1st parse
    try:
        v = json.loads(raw)
    except json.JSONDecodeError:
        return None  # plain text or bad JSON -> treat as None (or keep raw if you prefer)
    # handle "\"{...}\""
    if isinstance(v, str):
        try:
            return json.loads(v)
        except json.JSONDecodeError:
            return v  # it was a JSON string literal
    return v
