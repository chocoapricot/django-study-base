# helpers.py
import requests
from apps.system.settings.utils import my_parameter
from apps.system.apicache.utils import get_api_cache, set_api_cache

def fetch_company_info(corporate_number):
    # キャッシュをチェック
    cache_key = f"company_info_{corporate_number}"
    cached_data = get_api_cache(cache_key)
    if cached_data:
        return cached_data

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
            result = data["hojin-infos"][0]
            # キャッシュに保存
            validity_period = int(my_parameter("API_CACHE_VALIDITY_PERIOD", 86400))
            set_api_cache(cache_key, result, validity_period)
            return result
        else:
            return None  # 'hojin-infos' がない場合は None を返す
    return None  # APIリクエストが失敗した場合

def fetch_zipcode(zipcode):
    # キャッシュをチェック
    cache_key = f"zipcode_{zipcode}"
    cached_data = get_api_cache(cache_key)
    if cached_data:
        return cached_data

    base_url = my_parameter("ZIPCODE_API_PATH")
    if not base_url:
        return None
    url = f"{ base_url }{zipcode}"
    response = requests.get(url)
    # APIのレスポンスを確認
    if response.status_code == 200:
        data = response.json()
        # 'results'が存在し、かつNoneでなく、データがあれば返す
        if "results" in data and data["results"] and len(data["results"]) > 0:
            result = data["results"][0]
            # キャッシュに保存
            validity_period = int(my_parameter("API_CACHE_VALIDITY_PERIOD", 86400))
            set_api_cache(cache_key, result, validity_period)
            return result
        else:
            return None  # 'results' がない場合やNoneの場合は None を返す
    return None  # APIリクエストが失敗した場合
