import requests
import json
from apps.master.models import UserParameter

def call_gemini_api(prompt_text):
    """
    UserParameterマスタの設定を使ってGemini APIを呼び出す関数
    """
    # 設定値を取得
    try:
        api_key_param = UserParameter.objects.filter(pk='GEMINI_API_KEY').first()
        api_url_param = UserParameter.objects.filter(pk='GEMINI_API_URL').first()
        
        if not api_key_param or not api_url_param:
             return {"success": False, "error": "GEMINI_API_KEY または GEMINI_API_URL が設定値マスタに設定されていません。"}

        api_key = api_key_param.value
        api_url = api_url_param.value
        
    except Exception as e:
         return {"success": False, "error": f"設定取得エラー: {str(e)}"}

    if not api_key or not api_url:
        return {"success": False, "error": "APIキーまたはURLが空です。"}
        
    # URLにキーを含める処理
    if 'key=' not in api_url:
         target_url = f"{api_url}?key={api_key}"
    else:
         target_url = api_url
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    # Gemini APIのペイロード構造 (v1beta/v1)
    data = {
        "contents": [{
            "parts": [{"text": prompt_text}]
        }]
    }
    
    try:
        response = requests.post(target_url, headers=headers, json=data, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            # レスポンス構造からテキストを抽出
            try:
                text = result['candidates'][0]['content']['parts'][0]['text']
                return {"success": True, "text": text}
            except (KeyError, IndexError) as e:
                return {"success": False, "error": f"レスポンス解析エラー: {str(e)}", "raw": result}
        else:
            return {"success": False, "error": f"APIエラー: {response.status_code} - {response.text}"}
            
    except Exception as e:
        return {"success": False, "error": f"通信エラー: {str(e)}"}
