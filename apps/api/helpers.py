# helpers.py
import requests
import datetime
import re
from django.utils import timezone
from apps.system.apicache.utils import get_api_cache, set_api_cache
from apps.system.settings.utils import my_parameter
from apps.master.models import UserParameter

def fetch_company_info(corporate_number):
    # キャッシュをチェック
    cache_key = f"company_info_{corporate_number}"
    cached_data = get_api_cache(cache_key)
    if cached_data:
        return cached_data

    base_url = my_parameter("GBIZ_API_PATH",'https://info.gbiz.go.jp/hojin/v1/hojin/')
    url = f"{ base_url }{corporate_number}"
    token_param = UserParameter.objects.filter(pk='GBIZ_API_TOKEN').first()
    api_token = token_param.value if token_param and token_param.value else 'riGQUpnKTLCx8a9aCeyw7Gp4Hq3SJ2zs'

    headers = {
        "X-hojinInfo-api-token": api_token
    }
    response = requests.get(url, headers=headers)
    # APIのレスポンスを確認
    if response.status_code == 200:
        try:
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
        except requests.exceptions.JSONDecodeError:
            return None  # JSONのデコードに失敗した場合は None を返す
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

def fetch_municipality_name(muni_code):
    """muniCdから市区町村名を取得する。muni.jsをフェッチしてキャッシュする。"""
    if not muni_code:
        return ""
    
    cache_key = "gsi_muni_map"
    muni_map = get_api_cache(cache_key)
    
    if not muni_map:
        url = "https://maps.gsi.go.jp/js/muni.js"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                response.encoding = 'utf-8'
                text = response.text
                # GSI.MUNI_ARRAY["13101"] = '13,東京都,13101,千代田区'; のような形式をパース
                pattern = r'GSI\.MUNI_ARRAY\["(\d+)"\]\s*=\s*\'(.+?)\';'
                matches = re.findall(pattern, text)
                muni_map = {m[0]: m[1].split(',')[-1] for m in matches}
                
                # キャッシュに保存（1ヶ月）
                set_api_cache(cache_key, muni_map, 2592000)
        except Exception as e:
            print(f"Error fetching muni.js: {e}")
            return ""
            
    if muni_map:
        return muni_map.get(muni_code, "")
    return ""

def fetch_gsi_address(lat, lon):
    """国土地理院の逆ジオコーディングAPIを使用して緯度経度から住所を取得する"""
    from apps.system.settings.models import Dropdowns
    if not lat or not lon:
        return None
        
    # キャッシュをチェック (小数点以下4位程度で丸めてキーにする)
    try:
        flat = round(float(lat), 4)
        flon = round(float(lon), 4)
    except (ValueError, TypeError):
        return None
        
    cache_key = f"gsi_address_{flat}_{flon}"
    cached_data = get_api_cache(cache_key)
    if cached_data:
        return cached_data

    base_url = my_parameter("GSI_REVERSE_GEOCODER_API_PATH", "https://mreversegeocoder.gsi.go.jp/reverse-geocoder/LonLatToAddress")
    url = f"{base_url}?lon={lon}&lat={lat}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "results" in data:
                muni_code = data["results"].get("muniCd")
                lv01_nm = data["results"].get("lv01Nm", "")
                
                pref_code = muni_code[:2] if muni_code else None
                pref_name = Dropdowns.get_display_name('pref', pref_code) if pref_code else ""
                
                muni_name = fetch_municipality_name(muni_code)
                
                address = f"{pref_name}{muni_name}{lv01_nm}"
                
                # キャッシュに保存
                validity_period = int(my_parameter("API_CACHE_VALIDITY_PERIOD", 2592000)) # デフォルト1ヶ月
                set_api_cache(cache_key, address, validity_period)
                return address
    except Exception as e:
        print(f"GSI API Error: {e}")
        
    return None
