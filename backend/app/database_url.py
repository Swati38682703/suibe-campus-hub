def normalize_database_url(value: str) -> str:
    """Use the installed psycopg 3 driver for provider PostgreSQL URLs."""
    for prefix in ('postgresql://', 'postgres://'):
        if value.startswith(prefix):
            return 'postgresql+psycopg://' + value[len(prefix):]
    return value
