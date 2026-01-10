import requests
import json
from apps.master.models import GenerativeAiSetting
from apps.system.settings.utils import my_parameter

def call_gemini_api(prompt_text):
    """
    GenerativeAiSettingマスタの設定を使ってGemini APIを呼び出す関数
    """
    # 設定値を取得
    try:
        # AIプロバイダーを取得
        ai_provider_param = GenerativeAiSetting.objects.filter(pk='AI_PROVIDER').first()
        ai_provider = ai_provider_param.value if ai_provider_param else 'gemini'
        
        # AIプロバイダーがgeminiでない場合はエラー
        if ai_provider.lower() != 'gemini':
            return {"success": False, "error": "AIプロバイダーがGeminiに設定されていません。"}
        
        api_key_param = GenerativeAiSetting.objects.filter(pk='AI_API_KEY').first()
        model_param = GenerativeAiSetting.objects.filter(pk='AI_MODEL').first()
        api_url = my_parameter('GEMINI_API_URL')
        
        if not api_key_param or not model_param or not api_url:
             return {"success": False, "error": "AI_API_KEYまたはAI_MODELが生成AI設定に設定されていないか、GEMINI_API_URLがパラメータに設定されていません。"}

        api_key = api_key_param.value
        model = model_param.value
        
    except Exception as e:
         return {"success": False, "error": f"設定取得エラー: {str(e)}"}

    if not api_key or not api_url or not model:
        return {"success": False, "error": "APIキー、URL、またはモデルが空です。"}
        
    # URLにモデル名とキーを含める処理
    target_url = f"{api_url}{model}:generateContent?key={api_key}"
    
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
