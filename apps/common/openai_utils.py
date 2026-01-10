import requests
import json
from apps.master.models import GenerativeAiSetting
from apps.system.settings.utils import my_parameter

def call_openai_api(prompt_text):
    """
    GenerativeAiSettingマスタの設定を使ってOpenAI APIを呼び出す関数
    """
    # 設定値を取得
    try:
        # AIプロバイダーを取得
        ai_provider_param = GenerativeAiSetting.objects.filter(pk='AI_PROVIDER').first()
        ai_provider = ai_provider_param.value if ai_provider_param else 'gemini'
        
        # AIプロバイダーがopenaiでない場合はエラー
        if ai_provider.lower() != 'openai':
            return {"success": False, "error": "AIプロバイダーがOpenAIに設定されていません。"}
        
        api_key_param = GenerativeAiSetting.objects.filter(pk='AI_API_KEY').first()
        api_url = my_parameter('OPENAI_API_URL')
        model_param = GenerativeAiSetting.objects.filter(pk='AI_MODEL').first()

        if not api_key_param or not api_url:
             return {"success": False, "error": "AI_API_KEYが生成AI設定に設定されていないか、OPENAI_API_URLがパラメータに設定されていません。"}

        api_key = api_key_param.value
        model = model_param.value if model_param else "gpt-4"

    except Exception as e:
         return {"success": False, "error": f"設定取得エラー: {str(e)}"}

    if not api_key or not api_url:
        return {"success": False, "error": "APIキーまたはURLが空です。"}

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }

    # OpenAI APIのペイロード構造
    data = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt_text}
        ],
        "max_tokens": 2000,
        "temperature": 0.7
    }

    try:
        response = requests.post(api_url, headers=headers, json=data, timeout=60)

        if response.status_code == 200:
            result = response.json()
            # レスポンス構造からテキストを抽出
            try:
                text = result['choices'][0]['message']['content']
                return {"success": True, "text": text}
            except (KeyError, IndexError) as e:
                return {"success": False, "error": f"レスポンス解析エラー: {str(e)}", "raw": result}
        else:
            return {"success": False, "error": f"APIエラー: {response.status_code} - {response.text}"}

    except Exception as e:
        return {"success": False, "error": f"通信エラー: {str(e)}"}