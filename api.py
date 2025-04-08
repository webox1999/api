from flask import Flask, request, jsonify, Response
from helpers import api_request, get_car_info, get_client_id, get_client_orders, get_client_cars
from helpers import get_client_data, save_to_cache, get_by_ean, get_ean_by_brand_article, update_cache, get_sklad_id
from helpers import get_info_for_ean, parse_barcode
import requests, time, json
from flask_cors import CORS
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)




@app.route("/get_client", methods=["GET"])
def get_client_info():
    """Обрабатывает запрос, получает данные клиента и возвращает JSON-ответ."""
    phone_number = request.args.get("phone")
    API_KEY = request.args.get("api_key")
    if not phone_number:
        return jsonify({"error": "Введите номер телефона"}), 400

    client_data = get_client_id(phone_number, API_KEY)

    if not client_data:
        return jsonify({"error": "Клиент не найден"}), 404


    client_id = client_data["id"]
    client_name = client_data["name"]
    balance = client_data["balance"]
    create_date = client_data["create_date"]
    sum_trade = client_data["sum_trade"]

    if not client_id:
        return jsonify({"error": "Клиент не найден"}), 404

    orders = get_client_orders(client_id, API_KEY)
    cars = get_client_cars(client_id, API_KEY)
    cashback = get_client_data(client_id, API_KEY).get("company_cashback", [])

    return jsonify({
        "client_id": client_id,
        "name": client_name,
        "balance": balance,
        "reg_date": create_date,
        "oborot": sum_trade,
        "orders": orders,
        "cars": cars,
        "cashback": cashback
    })


@app.route("/get_payments", methods=["GET"])
def get_payments():
    start_date = request.args.get("start")
    end_date = request.args.get("end")
    API_KEY = request.args.get("api_key")
    payload = {
        "action": "get_payments",
        "from_date": start_date,
        "to_date":  end_date
    }
    response = api_request(payload, API_KEY)

    if response.status_code == 200:
        return response.json()


@app.route("/register_client", methods=["GET"])
def register_client():
    name = request.args.get("name")
    phone = request.args.get("phone")
    client_type = request.args.get("type")
    bonuses = request.args.get("bonuses")
    vin = request.args.get("vin")
    API_KEY = request.args.get("api_key")

    payload = {
        "action": "fast_save_company",
        "company_name": name,
        "mphone": phone,
        "okopf": client_type,
        "price_type": bonuses,
        "vin": vin if vin else "",
    }

    response = api_request(payload, API_KEY)

    if response.status_code == 200:
        return response.json()
    else:
        return {"error": "Failed to process request", "status_code": response.status_code}, response.status_code


@app.route("/add_car", methods=["GET"])
def add_car():
    vin = request.args.get("vin")
    client_id = request.args.get("id")
    API_KEY = request.args.get("api_key")

    if not vin:
        return {"error": "VIN is required"}, 400


    car_info = get_car_info(vin, API_KEY)


    if not car_info or car_info.get("engine_num") == "" or car_info.get("made_date") == "":
        return {"error": "Vehicle information not found", "vin": vin}, 404


    payload = {
        "action": "save_company_car",
        "company_id": client_id,
        "vin": vin,
        "engine_num": car_info["engine_num"],
        "made_date": car_info["made_date"],
    }


    response = api_request(payload, API_KEY)


    if response.status_code == 200:
        return response.json(), car_info
    else:
        return {"error": "Failed to process request", "status_code": response.status_code}, response.status_code


@app.route("/add_by_brand", methods=["GET"])
def add_by_brand():

    vin = request.args.get("vin")
    client_id = request.args.get("id")
    brand = request.args.get("brand")
    model = request.args.get("model")
    car_engine = request.args.get("engine")
    year = request.args.get("year")
    modification = request.args.get("type")
    car_id = request.args.get("car_id")
    API_KEY = request.args.get("api_key")
    payload = {
        "action": "save_company_car",
        "company_id": client_id,
        "company_car_id": car_id,
        "vin": vin,
        "engine_num": car_engine,
        "made_year": year,
        "auto_maker_id": brand,
        "auto_model": model,
        "auto_doc_num": modification
    }


    response = api_request(payload, API_KEY)


    if response.status_code == 200:
        return response.json(), payload

    else:
        return {"error": "Failed to process request", "status_code": response.status_code}, response.status_code


@app.route("/car_delete", methods=["GET"])
def car_delete():
    car_id = request.args.get("id")
    API_KEY = request.args.get("api_key")
    payload = {
        "action": "delete_company_car",
        "company_car_id": car_id,

    }
    response = api_request(payload, API_KEY)

    if response.status_code == 200:
        return response.json()


@app.route("/car_info", methods=["GET"])
def get_car_info_by_id():
    car_id = request.args.get("id")
    API_KEY = request.args.get("api_key")
    payload = {
        "action": "get_company_car",
        "company_car_id": car_id,

    }
    response = api_request(payload, API_KEY)

    if response.status_code == 200:
        return response.json()


@app.route("/get_brands", methods=["GET"])
def get_brands():
    payload = {
        "action": "get_auto_makers",
    }
    response = api_request(payload, None)

    if response.status_code == 200:
        return response.json()


@app.route("/get_models", methods=["GET"])
def get_models():
    car_id = request.args.get("id")

    payload = {
        "action": "get_auto_models",
        "auto_maker_id": car_id,
    }
    response = api_request(payload, None)

    if response.status_code == 200:
        return response.json()


@app.route("/get_profit", methods=["GET"])
def get_profit():
    phone = request.args.get("phone")
    start_date = request.args.get("start")
    end_date = request.args.get("end")
    API_KEY = request.args.get("api_key")
    data = get_client_id(phone, API_KEY)
    client_id = data.get("id")
    client_name = data.get("name")
    payload = {
        "action": "get_report_profit",
        "contragent_id":  client_id,
        "date_from": start_date,
        "date_to":  end_date,
    }
    response = api_request(payload, API_KEY)

    dealer_sum = response.json().get("dealer_sum")
    sale_sum = response.json().get("sale_sum")
    if response.status_code == 200:
        return jsonify({
            "client_id": client_id,
            "name": client_name,
            "dealer_sum": dealer_sum,
            "sale_sum": sale_sum
        })


@app.route("/add_code", methods=["GET"])
def add_codes():
    client_id = request.args.get("client_id")
    API_KEY = request.args.get("api_key")
    codes = request.args.get("code")
    client_data = get_client_data(client_id, API_KEY)
    check = client_data.get("descr")
    if check == "":
        code = f'Действующие купоны: [{codes}]'
    else:
        code = f'{check}  [{codes}]'
    payload = {
        "action": "save_company",
        "company_id": client_id,
        "descr": code,
        "show_descr": "on",
    }
    response = api_request(payload, API_KEY)

    if response.status_code == 200:
        return response.json()


@app.route("/delete_code", methods=["GET"])
def delete_codes():
    client_id = request.args.get("client_id")
    API_KEY = request.args.get("api_key")
    codes = request.args.get("code")
    client_data = get_client_data(client_id, API_KEY)
    check = client_data.get("descr")
    payload = {}
    if codes in check:
        payload = {
            "action": "save_company",
            "company_id": client_id,
            "descr": check.replace(f"[{codes}]", ""),
            "show_descr": "on"
        }
    else:
        return {'error': 'код не найден'}
    response = api_request(payload, API_KEY)

    if response.status_code == 200:
        return response.json()


@app.route("/change_name", methods=["GET"])
def change_name():
    new_name = request.args.get("new_name")
    client_id = request.args.get("id")
    API_KEY = request.args.get("api_key")
    client_data = get_client_data(client_id, API_KEY)

    old_name = client_data.get("name", "")

    # Проверяем наличие '%' в имени
    if "%" in old_name:
        # Вырезаем пометку для админа (сохраняем начиная с % и до конца)
        admin_note = old_name[old_name.index("%"):]
        new_name += f" {admin_note}"  # добавляем к новому имени с пробелом

    payload = {
        "action": "save_company",
        "company_id": client_id,
        "company_name": new_name.strip()
    }

    response = api_request(payload, API_KEY)


    if response.status_code == 200:
        return response.json()
    else:
        return jsonify({"error": "Failed to update name"}), response.status_code


session_abcp = requests.Session()
session_abcp.proxies.update({
    "http": "http://pczP5vLFkZ-mob-by:PC_1jSIh9Jg76kaDAPic@141.95.75.238:5959",
    "https": "http://pczP5vLFkZ-mob-by:PC_1jSIh9Jg76kaDAPic@141.95.75.238:5959"
})

headers_abcp = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Referer": "https://www.abcp.ru/",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",

}


@app.route("/get_ean", methods=["GET"])
def get_ean13():
    start_time = time.time()
    brand = request.args.get("brand")
    article = request.args.get("article")
    if not brand or not article:
        return jsonify({"status": "error", "message": "brand и article обязательны"}), 400


    cached_ean = get_ean_by_brand_article(brand, article)
    if cached_ean:
        elapsed = round(time.time() - start_time, 3)
        descr = get_by_ean(cached_ean)

        return Response(json.dumps({
            "status": "found",
            "from": "cache",
            "EAN-13": cached_ean,
            "descr": descr[0].get('descr'),
            "price": descr[0].get('price'),
            "time": elapsed
        }, ensure_ascii=False, indent=2), content_type="application/json; charset=utf-8")

    # Если не найдено — парсим
    url = f"https://www.abcp.ru/parts/{brand}/{article}"

    try:
        response = session_abcp.get(url, headers=headers_abcp, timeout=10)
    except requests.RequestException as e:
        return jsonify({"status": "error", "message": f"Ошибка при запросе: {str(e)}"}), 500

    if response.status_code != 200:
        return jsonify({"status": "error", "message": "Не удалось получить страницу"}), 502

    soup = BeautifulSoup(response.text, 'html.parser')
    ean_block = soup.find("span", class_="property", string="EAN-13: ")


    descr_block = soup.select_one(
        "body > div.siteWrapper.bodyBlur > div > div > div.wGoodsGroupInfo > div.goodsInfoColumns.goodsInfoColumnsGridLayout > div.goodsInfoDescrColumn > div > h1 > div")
    descr = descr_block.get_text(strip=True) if descr_block else None

    if ean_block and ean_block.find_next_sibling("span"):
        ean_value = ean_block.find_next_sibling("span").text.strip()
        elapsed = round(time.time() - start_time, 3)
        data = {
            "status": "found",
            "from": "api",
            "EAN-13": ean_value,
            "descr": descr,
            "time": elapsed
        }
        save_to_cache(ean_value, brand, article, descr)

        return Response(json.dumps(data, ensure_ascii=False, indent=2), content_type="application/json; charset=utf-8")

    else:
        elapsed = round(time.time() - start_time, 3)
        return jsonify({
            "time": elapsed,
            "status": "not_found",
            "EAN-13": None,
            "descr": descr
        })


@app.route("/get_info_by_ean", methods=["GET"])
def reverse_ean():
    start_time = time.time()
    ean = request.args.get("ean")
    if not ean:
        return Response(
            json.dumps({"status": "error", "message": "ean обязательный параметр"}, ensure_ascii=False),
            content_type="application/json; charset=utf-8"
        ), 400


    cached_data = get_by_ean(ean)
    elapsed = round(time.time() - start_time, 3)

    if cached_data:
        if len(cached_data) == 1:
            brand = cached_data[0]['brand']
            article = cached_data[0]['article']
            descr = cached_data[0].get('descr')
            price = cached_data[0].get('price')
            return Response(json.dumps({
                "status": "found",
                "from": "cache",
                "brand": brand,
                "article": article,
                "descr": descr,
                "price": price,
                "time": elapsed
            }, ensure_ascii=False, indent=2), content_type="application/json; charset=utf-8")
        else:
            return Response(json.dumps({
                "status": "found",
                "from": "cache",
                "EAN-13": ean,
                "results": cached_data,
                "count": len(cached_data),
                "time": elapsed
            }, ensure_ascii=False, indent=2), content_type="application/json; charset=utf-8")


    url = f"https://www.abcp.ru/search?pcode={ean}"

    try:
        response = session_abcp.get(url, headers=headers_abcp, timeout=10)
    except requests.RequestException as e:
        return Response(
            json.dumps({"status": "error", "message": f"Ошибка при запросе: {str(e)}"}, ensure_ascii=False),
            content_type="application/json; charset=utf-8"
        ), 500

    if response.status_code != 200:
        return Response(
            json.dumps({"status": "error", "message": "Не удалось получить страницу"}, ensure_ascii=False),
            content_type="application/json; charset=utf-8"
        ), 502

    soup = BeautifulSoup(response.text, 'html.parser')


    h1 = soup.find("h1", class_="brand")
    if h1:
        link = h1.find("a", class_="infoColumnLink")
        brand_tag = link.find("span", class_="article-brand") if link else None
        article_tag = link.find("span", class_="article-number") if link else None

        descr = None
        parts = h1.decode_contents().split("<br>")
        if len(parts) > 1:
            descr = BeautifulSoup(parts[1], 'html.parser').get_text(strip=True)

        if brand_tag and article_tag:
            brand = brand_tag.text.strip()
            article = article_tag.text.strip()
            save_to_cache(ean, brand, article, descr)

            data = {
                "status": "found",
                "from": "api",
                "brand": brand,
                "article": article,
                "descr": descr,
                "time": round(time.time() - start_time, 3)
            }
            return Response(json.dumps(data, ensure_ascii=False, indent=2),
                            content_type="application/json; charset=utf-8")


    results = []
    table = soup.select_one("table > tbody")
    if table:
        rows = table.find_all("tr", class_="startSearching")
        for row in rows:
            brand_tag = row.find("td", class_="caseBrand")
            article_tag = row.find("td", class_="casePartCode")
            descr_tag = row.find("td", class_="caseDescription")

            brand = brand_tag.get_text(strip=True) if brand_tag else None
            article = article_tag.get_text(strip=True) if article_tag else None
            descr = descr_tag.get_text(strip=True) if descr_tag else None

            if brand and article:
                save_to_cache(ean, brand, article, descr)
                results.append({
                    "brand": brand,
                    "article": article,
                    "descr": descr
                })

    if results:
        data = {
            "status": "found",
            "from": "api",
            "results": results,
            "count": len(results),
            "time": round(time.time() - start_time, 3)
        }
        return Response(json.dumps(data, ensure_ascii=False, indent=2),
                        content_type="application/json; charset=utf-8")
    else:
        second_check = parse_barcode(ean)
        return second_check


@app.route("/get_sellers", methods=["GET"])
def get_sellers():
    profile_id = request.args.get("id")
    API_KEY = request.args.get("api_key")
    payload = {
        "action": "get_plugins",
        "profile_id": profile_id
    }
    response = api_request(payload, API_KEY)

    if response.status_code == 200:
        return response.json()

    return response.json()


@app.route("/save_new_details", methods=["GET"])
def save_new_details():
    ean = request.args.get("ean")
    brand = request.args.get("brand")
    article = request.args.get("article")
    descr = request.args.get("descr")
    price = request.args.get("price")

    save_to_cache(ean, brand, article, descr, price)
    result = {
        "status": "ok"
    }
    return result




@app.route("/update_price", methods=["GET"])
def update_price():
    ean = request.args.get("ean")
    brand = request.args.get("brand")
    article = request.args.get("article")
    descr = request.args.get("descr")
    price = request.args.get("price")

    update_cache(ean, brand, article, descr, price)
    result = {
        "status": "updated"

    }
    return result





@app.route("/get_document_details", methods=["GET"])
def get_document_details():
    document_id = request.args.get("document_id")
    API_KEY = request.args.get("api_key")
    sklad_id = get_sklad_id(document_id, API_KEY)


    payload = {
        "action": "get_document_details",
        "document_id": document_id,
        "page": "1",
        "sklad_id": sklad_id
    }

    response = api_request(payload, API_KEY)
    if response.status_code != 200:
        return {"error": "Ошибка при получении первой страницы"}, response.status_code

    data = response.json()
    all_details = data.get("document_details", [])
    total_pages = int(data.get("document_pages", 1))


    for page in range(2, total_pages + 1):
        payload["page"] = str(page)
        page_response = api_request(payload, API_KEY)

        if page_response.status_code == 200:
            page_data = page_response.json()
            page_details = page_data.get("document_details", [])
            all_details.extend(page_details)
        else:
            print(f"⚠ Ошибка загрузки страницы {page}: {page_response.status_code}")


    data["document_details"] = all_details
    data["document_pages"] = total_pages

    return jsonify(data)




@app.route("/save_ean", methods=["GET"])
def save_ean():
    API_KEY = request.args.get("api_key")
    detail_id = request.args.get("detail_id")
    ean = request.args.get("ean")
    detail_payload = get_info_for_ean(detail_id, API_KEY)
    detail_payload.update({
        "action": "save_document_detail",
        "ean13": ean,
    })
    response = api_request(detail_payload, API_KEY)

    if response.status_code == 200:
        return response.json()

    return response.json()






if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8060, debug=True)
