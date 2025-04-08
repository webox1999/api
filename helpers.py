from flask import request
import requests, time, json, os
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

URL = "https://sort1.pro/api/index.php"
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"

}
SESSIONS = {}

def get_session(api_key):
    if api_key not in SESSIONS:
        s = requests.Session()
        s.headers.update(HEADERS)
        SESSIONS[api_key] = s
    return SESSIONS[api_key]

def api_request(payload, api_key):
    session = get_session(api_key)
    payload = dict(payload)
    payload["api_key"] = api_key
    return session.post(URL, json=payload)


def get_default_start_date():
    return (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")


def get_car_info(vin, API_KEY):
    """Запрашивает полную информацию об авто."""
    payload = {"action": "get_car_by_vin", "vin": vin}
    response = api_request(payload, API_KEY)

    if response.status_code == 200:
        car_info = response.json().get("car", [])

        if car_info:
            return {
                "engine_num": car_info.get("engine_num", 'Нет данных'),
                "made_date": car_info.get("made_date", 'Нет данных')
            }

    return None


def get_client_id(phone_number, API_KEY):
    """Ищет клиента по номеру телефона и возвращает всю информацию о нём."""
    payload = {
        "action": "get_clients",
        "page": "1",
        "search_clients_client_name": phone_number
    }

    response = api_request(payload, API_KEY)


    if response.status_code == 200:
        clients = response.json().get("clients", [])

        if clients:
            client = clients[0]
            return {
                "id": client.get("id"),
                "name": client.get("name"),
                "balance": client.get("company_balance"),
                "create_date": client.get("create_date"),
                "sum_trade": client.get("sum_trade")
            }

    return None



def get_client_orders(client_id, API_KEY):
    """Запрашивает заказы клиента."""
    payload = {"action": "get_client_zakaz_details", "company_id": int(client_id)}
    response = api_request(payload, API_KEY)


    if response.status_code == 200:
        return response.json().get("zakaz_details", [])

    return []


def get_client_cars(client_id, API_KEY):
    """Запрашивает автомобили клиента."""
    payload = {"action": "get_company_cars", "company_id": int(client_id)}
    response = api_request(payload, API_KEY)


    if response.status_code == 200:
        return response.json().get("company_cars", [])

    return []

def get_client_data(client_id, API_KEY):
    """Запрашивает полную информацию о клиенте. Берет только кэшбек (Можно вытащить всю инфу)"""
    payload = {"action": "get_company", "company_id": int(client_id)}
    response = api_request(payload, API_KEY)


    if response.status_code == 200:
        return response.json()

    return []

def save_to_cache(ean, brand, article, descr=None, price=None, filename="ean_cache.json"):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            try:
                cache = json.load(f)
            except json.JSONDecodeError:
                cache = {}
    else:
        cache = {}

    article_clean = article.strip().lower()
    brand_clean = brand.strip().lower()

    new_entry = {"brand": brand.strip(), "article": article.strip()}
    if descr:
        new_entry["descr"] = descr.strip()
    if price:
        new_entry["price"] = price.strip()

    exists = False
    if ean in cache:
        for item in cache[ean]:
            if item["article"].strip().lower() == article_clean:
                exists = True
                break

        if not exists:
            cache[ean].append(new_entry)
    else:
        cache[ean] = [new_entry]

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def get_by_ean(ean, filename="ean_cache.json"):
    import json

    try:
        with open(filename, "r", encoding="utf-8") as f:
            cache = json.load(f)
        return cache.get(ean)
    except Exception as e:
        print(f"Ошибка при чтении кэша: {e}")
        return None


def get_ean_by_brand_article(brand, article, filename="ean_cache.json"):
    import json

    brand = brand.strip().lower()
    article = article.strip().lower()

    try:
        with open(filename, "r", encoding="utf-8") as f:
            cache = json.load(f)

        for ean, entries in cache.items():
            for entry in entries:
                if entry["brand"].strip().lower() == brand and entry["article"].strip().lower() == article:
                    return ean
        return None
    except Exception as e:
        print(f"Ошибка при чтении кэша: {e}")
        return None


def update_cache(ean, brand, article, descr, price, filename="ean_cache.json"):

    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            try:
                cache = json.load(f)
            except json.JSONDecodeError:
                cache = {}
    else:
        cache = {}


    brand = brand.strip().lower()
    article = article.strip().lower()

    updated = False


    if ean not in cache:
        cache[ean] = [{
            "brand": brand,
            "article": article,
            "descr": descr,
            "price": price
        }]
        updated = True
    else:

        for item in cache[ean]:
            if item["brand"].strip().lower() == brand and item["article"].strip().lower() == article:
                item["price"] = price
                updated = True
                break


        if not updated:
            cache[ean].append({
                "brand": brand,
                "article": article,
                "descr": descr,
                "price": price
            })
            updated = True


    if updated:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)

def get_sklad_id(document_id, API_KEY):
    document_id = request.args.get("document_id")

    payload = {
        "action": "get_document",
        "document_id": document_id,
    }
    response = api_request(payload, API_KEY)
    data = json.loads(response.text)

    sklad_id = data["document"]["sklad_id"]
    return sklad_id


def get_info_for_ean(document_detail_id, API_KEY):
    payload = {"document_detail_id": document_detail_id, "action": "get_document_detail"}
    response = api_request(payload, API_KEY)
    data = json.loads(response.text)

    detail = data.get("document_details", [])[0]

    payload = {
        "article": detail.get("article"),
        "brand": detail.get("brand"),
        "brand_id": detail.get("brand_id"),
        "change_sklad_name": "on",
        "count": detail.get("count"),
        "detail_id": detail.get("detail_id"),
        "detail_size": detail.get("detail_size"),
        "document_detail_group_id": detail.get("detail_group_id", ""),
        "document_detail_group_name": detail.get("detail_group_name", ""),
        "document_id": detail.get("document_id"),
        "id": detail.get("id"),
        "markup": detail.get("markup"),
        "my_code": detail.get("my_code"),
        "name": detail.get("name"),
        "price": detail.get("price"),
        "price_without_nds": detail.get("price"),
        "sale_price": detail.get("sale_price"),
        "sell_count": detail.get("sell_count"),
        "sklad_id": detail.get("sklad_id"),
        "subaction": "edit",
        "tax": detail.get("tax"),
        "time": detail.get("time")
    }
    return payload

session_barcode = requests.Session()

headers_barcode = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Referer": "https://www.google.com/",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",

}

def parse_barcode(barcode):
    start_time = time.time()
    url = f"https://barcode-list.ru/barcode/RU/Поиск.htm?barcode={barcode}"

    try:
        response = session_barcode.get(url, headers=headers_barcode, timeout=10)
        response.raise_for_status()
    except Exception as e:
        return {
            "status": "error",
            "message": f"Ошибка при запросе: {e}",
            "time": round(time.time() - start_time, 3)
        }

    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", class_="randomBarcodes")

    if not table:
        return {
            "status": "not_found",
            "from": "barcode",
            "results": [],
            "count": 0,
            "time": round(time.time() - start_time, 3)
        }

    rows = table.find_all("tr")[1:]
    results = []

    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 5:
            descr = cols[2].text.strip()
            match = cols[4].text.strip()
            result = {
                "brand": "None",
                "article": "None",
                "descr": descr,
                "ean": barcode,
                "match": int(match) if match.isdigit() else 0
            }
            results.append(result)

    return {
        "status": "found" if results else "not_found",
        "from": "barcode",
        "results": results,
        "count": len(results),
        "time": round(time.time() - start_time, 3)
    }
