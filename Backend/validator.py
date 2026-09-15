import re


class SQLValidationError(Exception):
    """Custom exception raised when SQL fails security criteria."""

    pass


ALLOWED_TABLES = {"draws"}


def validate_sql_query(sql_query: str) -> str:
    clean_query = sql_query.strip().rstrip(";")

    # Rule 1: Block multi-statement queries
    if ";" in clean_query:
        raise SQLValidationError("Multiple SQL statements are strictly forbidden.")

    # Rule 2: Enforce READ-ONLY operations
    if not re.match(r"^\s*SELECT\b", clean_query, re.IGNORECASE):
        raise SQLValidationError("Only SELECT statements are permitted.")

    # Rule 3: Block write and DDL operations
    forbidden_keywords = [
        r"\bINSERT\b",
        r"\bUPDATE\b",
        r"\bDELETE\b",
        r"\bDROP\b",
        r"\bALTER\b",
        r"\bCREATE\b",
        r"\bTRUNCATE\b",
        r"\bEXEC\b",
        r"\bATTACH\b",
        r"\bDETACH\b",
        r"\bPRAGMA\b",
    ]
    for pattern in forbidden_keywords:
        if re.search(pattern, clean_query, re.IGNORECASE):
            raise SQLValidationError(
                f"Forbidden SQL operation detected: '{pattern}'"
            )

    # Rule 4: Whitelist target tables
    tables_found = re.findall(
        r"\bFROM\s+([a-zA-Z0-9_]+)", clean_query, re.IGNORECASE
    )
    for table in tables_found:
        if table.lower() not in ALLOWED_TABLES:
            raise SQLValidationError(
                f"Access to table '{table}' is unauthorized."
            )

    return clean_query