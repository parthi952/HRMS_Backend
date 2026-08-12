import os
import json
from fastapi import APIRouter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, "CurrencyJson.Json")

router = APIRouter(tags=["currency list"])

def get_currency_data():
    with open(JSON_PATH, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data

@router.get("/")
def list_of_currency():
    return get_currency_data()