import uuid

def parse_uuid(uuid_str):
    """Convert a string to a UUID object, return None if invalid"""
    try:
        return uuid.UUID(uuid_str)
    except (ValueError, AttributeError, TypeError):
        return None
