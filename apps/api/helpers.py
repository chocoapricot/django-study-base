# helpers.py
import requests
from apps.system.parameters.utils import my_parameter

def fetch_company_info(corporate_number):
    base_url = my_parameter("GBIZ_API_PATH",'https://info.gbiz.go.jp/hojin/v1/hojin/')
    url = f"{ base_url }{corporate_number}"
    headers = {
        "X-hojinInfo-api-token": my_parameter("GBIZ_API_TOKEN",'riGQUpnKTLCx8a9aCeyw7Gp4Hq3SJ2zs')
    }
    response = requests.get(url, headers=headers)
    # APIのレスポンスを確認
    if response.status_code == 200:
        data = response.json()
        # 'hojin-infos'が存在するか確認し、データがあれば返す
        if "hojin-infos" in data and data["hojin-infos"] and len(data["hojin-infos"]) > 0:
            return data["hojin-infos"][0]  # 最初の企業情報を返す
        else:
            return None  # 'hojin-infos' がない場合は None を返す
    return None  # APIリクエストが失敗した場合

def fetch_zipcode(zipcode):
    base_url = my_parameter("ZIPCODE_API_PATH")
    url = f"{ base_url }{zipcode}"
    response = requests.get(url)
    # APIのレスポンスを確認
    if response.status_code == 200:
        data = response.json()
        # 'results'が存在し、かつNoneでなく、データがあれば返す
        if "results" in data and data["results"] and len(data["results"]) > 0:
            return data["results"][0]  # 最初の住所情報を返す
        else:
            return None  # 'results' がない場合やNoneの場合は None を返す
    return None  # APIリクエストが失敗した場合
