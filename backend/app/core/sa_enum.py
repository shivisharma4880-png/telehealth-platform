"""Helpers for SQLAlchemy Enum columns: persist str Enum *values* (e.g. 'admin') not member names (e.g. 'ADMIN')."""


def enum_values(enum_cls):
    return [m.value for m in enum_cls]
