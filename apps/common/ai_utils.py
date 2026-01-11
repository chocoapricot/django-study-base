
def run_ai_check(prompt_key, contract_text, default_prompt):
    """
    AIチェックの共通ロジック
    """
    from apps.master.models import GenerativeAiSetting
    from apps.common.gemini_utils import call_gemini_api
    from apps.common.openai_utils import call_openai_api
    import markdown

    # AIプロバイダーを取得
    ai_provider_param = GenerativeAiSetting.objects.filter(pk='AI_PROVIDER').first()
    ai_provider = ai_provider_param.value if ai_provider_param else 'gemini'  # デフォルトはgemini

    prompt_template_param = GenerativeAiSetting.objects.filter(pk=prompt_key).first()
    prompt_template = prompt_template_param.value if prompt_template_param else ""

    if not prompt_template:
        prompt_template = default_prompt

    final_prompt = prompt_template.replace('{{contract_text}}', contract_text)

    # AIプロバイダーに応じてAPIを呼び出す
    if ai_provider.lower() == 'openai':
        result = call_openai_api(final_prompt)
    else:
        result = call_gemini_api(final_prompt)

    ai_response = None
    error_message = None

    if result['success']:
        # MarkdownをHTMLに変換（nl2br拡張を使用して改行を保持）
        ai_response = markdown.markdown(result['text'], extensions=['nl2br', 'fenced_code', 'tables'])
    else:
        error_message = result['error']

    return ai_response, error_message
