import requests
import json
import time
import os

# ==========================================
# AEGIS-AGENT: THE AI BRAIN
# ==========================================

# 1. SETTINGS
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
GEMINI_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={key}"

_mistral_model_override = os.getenv("MISTRAL_MODELS", "").strip()
MISTRAL_MODELS = [
    model.strip()
    for model in (
        _mistral_model_override.split(",")
        if _mistral_model_override
        else ["mistral-small-latest", "mistral-large-latest"]
    )
    if model.strip()
]

_gemini_model_override = os.getenv("GEMINI_MODELS", "").strip()
GEMINI_MODELS = [
    model.strip()
    for model in (
        _gemini_model_override.split(",")
        if _gemini_model_override
        else ["gemini-2.5-flash-lite", "gemini-2.0-flash-lite-001", "gemini-2.0-flash-lite"]
    )
    if model.strip()
]

_provider_override = os.getenv("AI_PROVIDER", "auto").strip().lower()
AI_PROVIDER = _provider_override if _provider_override in {"auto", "mistral", "gemini"} else "auto"

_provider_order_override = os.getenv("AI_PROVIDER_ORDER", "").strip().lower()
if _provider_order_override:
    parsed = [p.strip() for p in _provider_order_override.split(",") if p.strip()]
    parsed = [p for p in parsed if p in {"mistral", "gemini"}]
    PROVIDER_ORDER = parsed if parsed else ["mistral", "gemini"]
else:
    PROVIDER_ORDER = ["mistral", "gemini"]


def _env_bool(name, default=True):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


AI_ENABLE_FALLBACK = _env_bool("AI_ENABLE_FALLBACK", True)

# 2. THE RULEBOOK (System Prompt)
# 2. THE RULEBOOK (System Prompt)
SYSTEM_PROMPT = """
You are Aegis-Agent, an advanced, autonomous API Security DAST Engine.
Your goal is to completely map an unknown API and discover vulnerabilities like Mass Assignment or Data Leaks.

You have no prior knowledge of the target. You must dynamically discover its structure.
You have access to the following tools:
1. "network_recon": Scans an IP for open ports.
   - Input: {"target_ip": "<ip>"}
2. "local_directory_mapper": Scans a base URL for common paths (like /swagger.json, /docs).
   - Input: {"base_url": "<url>"}
3. "parse_api_schema": Extracts all routes from an OpenAPI/Swagger JSON file.
   - Input: {"schema_url": "<url_to_json_file>"}
4. "universal_http_client": Sends HTTP requests to specific endpoints.
   - Input: {"method": "<GET/POST/PUT>", "url": "<url>", "payload": "<json_string_if_needed>"}

METHODOLOGY:
1. Recon the target IP.
2. Map the directories to find API documentation (e.g., swagger.json).
3. If you find a schema JSON file, parse it using "parse_api_schema" to get the exact API blueprint.
4. Use the blueprint to construct targeted HTTP requests against the discovered endpoints.
5. If you find leaked data, passwords, or unauthorized admin access, set action to "REPORT_VULNERABILITY" and summarize.

You MUST respond ONLY with a raw JSON object.

EXPECTED JSON FORMAT:
{
  "thought": "Your tactical reasoning for the next step.",
  "action": "The exact name of the tool to use (or REPORT_VULNERABILITY)",
  "action_input": {
      "key": "value"
  }
}
"""

def _normalize_text(raw_text):
    if isinstance(raw_text, list):
        joined = []
        for item in raw_text:
            if isinstance(item, dict):
                joined.append(item.get("text", ""))
            else:
                joined.append(str(item))
        raw_text = "".join(joined)

    return str(raw_text).replace("```json", "").replace("```", "").strip()


def _build_user_prompt(memory_bank):
    recent_memory = memory_bank[-12:]
    compact_memory = [
        item if len(item) <= 400 else item[:400] + " ...[truncated]"
        for item in recent_memory
    ]
    return "=== MEMORY LOG ===\n" + "\n".join(compact_memory)


def _is_quota_or_rate_limit(response):
    if response.status_code == 429:
        return True
    if response.status_code in {400, 403}:
        body = response.text.lower()
        return "quota" in body or "rate" in body or "resource_exhausted" in body
    return False


def talk_to_mistral(memory_bank):
    """Sends memory to Mistral and returns the next action JSON as text."""
    if not MISTRAL_API_KEY:
        print("   [❌ API ERROR] MISTRAL_API_KEY is missing.")
        return None

    user_prompt = _build_user_prompt(memory_bank)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
    }

    for model in MISTRAL_MODELS:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 500,
        }

        try:
            response = requests.post(MISTRAL_URL, headers=headers, json=payload, timeout=40)
            
            if response.status_code == 200:
                data = response.json()
                raw_text = data["choices"][0]["message"]["content"]
                return _normalize_text(raw_text)
            
            elif _is_quota_or_rate_limit(response):
                print(f"   [⏳ QUOTA HIT] {model} is rate-limited. Trying next model...")
                time.sleep(2)
                continue
            else:
                print(f"   [DEBUG] Model {model} failed with {response.status_code}")
                continue
                
        except Exception as e:
            print(f"   [DEBUG] Request error: {e}")
            continue
            
    print("   [❌ API ERROR] All configured Mistral models failed. Check key, model access, or quota.")
    return None


def talk_to_gemini(memory_bank):
    """Sends memory to Gemini and returns the next action JSON as text."""
    if not GEMINI_API_KEY:
        print("   [DEBUG] GEMINI_API_KEY is missing. Skipping Gemini provider.")
        return None

    full_prompt = SYSTEM_PROMPT + "\n\n" + _build_user_prompt(memory_bank)
    headers = {"Content-Type": "application/json"}

    for model in GEMINI_MODELS:
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 500,
            },
        }
        url = GEMINI_URL_TEMPLATE.format(model=model, key=GEMINI_API_KEY)

        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=40)

            if response.status_code == 200:
                data = response.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                return _normalize_text(raw_text)

            elif _is_quota_or_rate_limit(response):
                print(f"   [⏳ QUOTA HIT] {model} is rate-limited. Trying next model...")
                time.sleep(2)
                continue
            else:
                print(f"   [DEBUG] Model {model} failed with {response.status_code}")
                continue

        except Exception as e:
            print(f"   [DEBUG] Gemini request error: {e}")
            continue

    print("   [❌ API ERROR] All configured Gemini models failed. Check key, model access, or quota.")
    return None


def talk_to_ai(memory_bank, provider=None):
    """Primary AI entrypoint with provider choice and automatic backup failover."""
    selected = (provider or AI_PROVIDER or "auto").strip().lower()

    if selected == "mistral":
        providers = ["mistral", "gemini"] if AI_ENABLE_FALLBACK else ["mistral"]
    elif selected == "gemini":
        providers = ["gemini", "mistral"] if AI_ENABLE_FALLBACK else ["gemini"]
    else:
        providers = PROVIDER_ORDER if AI_ENABLE_FALLBACK else PROVIDER_ORDER[:1]

    if not providers:
        providers = ["mistral", "gemini"] if AI_ENABLE_FALLBACK else ["mistral"]

    for current in providers:
        if current == "mistral":
            response = talk_to_mistral(memory_bank)
        else:
            response = talk_to_gemini(memory_bank)

        if response:
            return response

        print(f"   [INFO] Switching provider from {current} to backup...")

    print("   [❌ API ERROR] No AI providers available right now.")
    return None

# ==========================================
# TEST BLOCK (Runs only if executed directly)
# ==========================================
if __name__ == "__main__":
    print("🧠 Waking up Aegis-Agent Brain...")
    
    fake_memory = ["INSTRUCTION: Begin audit on target localhost."]
    print("🧠 Asking AI for its first move...")
    
    print(f"🧪 Provider mode: {AI_PROVIDER} (order: {', '.join(PROVIDER_ORDER)})")
    ai_response = talk_to_ai(fake_memory)
    
    if ai_response:
        print("\n=== RAW AI RESPONSE ===")
        print(ai_response)
        print("=======================")
        
        try:
            parsed = json.loads(ai_response)
            print("\n✅ SUCCESS: The AI Brain successfully formatted its thoughts as a machine-readable JSON object!")
            print(f"Next Action Chosen: {parsed.get('action')}")
        except json.JSONDecodeError:
            print("\n❌ FAILED: The AI did not output valid JSON.")
    else:
        print("\n❌ FAILED: The AI could not be reached.")