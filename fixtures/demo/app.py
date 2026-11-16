"""Intentionally unsafe synthetic fixture. Do not run as an application."""
from service import evaluate

def handler(payload):
    return evaluate(payload)
