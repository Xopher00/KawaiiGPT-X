#!/usr/bin/env python3
"""
KawaiiGPT Backend Server
Routes requests to different AI providers based on the provider field
"""
from flask import Flask, request, Response, jsonify, stream_with_context
import requests
import json
import os
import urllib.parse
import random
import time
import copy
from injection_engine import prompt_injection
from stream_monitor import generate, RefusalDetectedException

app = Flask(__name__)

# Enable/disable injection (for security testing)
INJECTION_ENABLED = os.getenv('INJECTION_ENABLED', 'true').lower() == 'true'

# Enable/disable refusal detection and retry with mutations (EXPERIMENTAL - disabled by default)
REFUSAL_DETECTION_ENABLED = os.getenv('REFUSAL_DETECTION_ENABLED', 'false').lower() == 'true'

# Load API keys from environment or config file
POLLINATIONS_API_KEY = os.getenv('POLLINATIONS_API_KEY', '')
if not POLLINATIONS_API_KEY and os.path.exists('.pollinations_api_key'):
    with open('.pollinations_api_key', 'r') as f:
        POLLINATIONS_API_KEY = f.read().strip()

# Provider configurations
PROVIDERS = {
    'PollinationsAI': {
        'chat_url': 'https://enter.pollinations.ai/api/generate/v1/chat/completions',
        'requires_auth': True
    },
    'PollinationsImage': {
        'image_url': 'https://enter.pollinations.ai/api/generate/image',
        'requires_auth': True
    }
}

def route_to_pollinations_chat(payload, auth_header, attempt=0):
    """Route chat completion request to Pollinations API with optional injection"""
    model = payload.get('model', 'openai')
    messages = payload.get('messages', [])
    tools = payload.get('tools')

    print(f"\n[Backend] ===== NEW REQUEST =====", flush=True)
    print(f"[Backend] Model: {model}", flush=True)
    print(f"[Backend] Messages: {len(messages)}, Tools: {bool(tools)}", flush=True)
    print(f"[Backend] Attempt: {attempt + 1}", flush=True)

    # Apply prompt injection if enabled
    if INJECTION_ENABLED:
        from injection_engine import MODEL_INJECTION_MAP
        if model in MODEL_INJECTION_MAP:
            messages = prompt_injection(model_name=model, original_messages=messages, attempt=attempt)
            print(f"[Backend] ✓ Applied injection for {model}", flush=True)
        else:
            print(f"[Backend] ✗ No injection mapping for {model}", flush=True)

    # Print user request (the most recent 'user' message)
    user_request = next(
        (msg for msg in reversed(messages) if msg.get("role") == "user"),
        None
    )
    print(f"\n[Backend] User Request:\n{json.dumps(user_request, indent=2) if user_request else '--NONE--'}\n", flush=True)

    # Build request payload
    pollinations_payload = {
        "model": model,
        "messages": messages,
        "stream": True
    }
    if tools:
        pollinations_payload["tools"] = tools

    # Make request with auth if available
    headers = {"content-type": "application/json"}
    if auth_header:
        headers['Authorization'] = auth_header
    elif POLLINATIONS_API_KEY:
        headers["Authorization"] = f"Bearer {POLLINATIONS_API_KEY}"        

    return requests.post(
        PROVIDERS['PollinationsAI']['chat_url'],
        headers=headers,
        json=pollinations_payload,
        stream=True,
        timeout=(60, 600)  # (connect timeout, read timeout)
    )

def route_to_pollinations_image(payload, auth_header):
    """Shared Image Logic"""
    prompt = payload.get('prompt', '')
    
    # Extract from messages if prompt is missing (Continue.dev style)
    if not prompt and 'messages' in payload:
        for msg in reversed(payload['messages']):
            if msg.get('role') == 'user':
                content = msg.get('content', '')
                if isinstance(content, str): prompt = content
                elif isinstance(content, list): 
                    prompt = " ".join([p.get('text','') for p in content if p.get('type')=='text'])
                break
    
    if not prompt: return None, "No prompt found"

    model = payload.get('model', 'flux')
    seed = random.randint(0, 999999)
    encoded = urllib.parse.quote(prompt)
    
    # OpenAI standard uses 'size' (1024x1024), we convert to width/height
    size = payload.get('size', '1024x1024')
    w, h = 1024, 1024
    if '16' in size and '9' in size: w, h = 1024, 576 # Basic logic
    
    base_url = PROVIDERS['PollinationsImage']['image_url']
    final_url = f"{base_url}/{encoded}?model={model}&width={w}&height={h}&seed={seed}&nologo=true"
    
    print(f"Image URL: {final_url}")

    # For Open WebUI, we stream the binary!
    try:
        headers = {"User-Agent": "KawaiiGPT"}
        if auth_header:
            headers["Authorization"] = auth_header
        elif POLLINATIONS_API_KEY:
            headers["Authorization"] = f"Bearer {POLLINATIONS_API_KEY}"
        resp = requests.get(final_url, headers=headers, stream=True, timeout=60)
        return resp, None
    except Exception as e:
        return None, str(e)

# A wrapper function that handles multiple attempts at prompt injection against a model
def retrying_generate(payload, auth_header, max_attempts=10):
    orig_payload = copy.deepcopy(payload)
    attempt = 0

    # If refusal detection is disabled, just stream once without retry
    if not REFUSAL_DETECTION_ENABLED:
        response = route_to_pollinations_chat(payload, auth_header, attempt=0)
        for chunk in generate(response, detect_refusal=False):
            yield chunk
        return

    # Refusal detection enabled - retry on detection
    while attempt < max_attempts:
        attempt_payload = copy.deepcopy(orig_payload)
        response = route_to_pollinations_chat(attempt_payload, auth_header, attempt=attempt)
        try:
            for chunk in generate(response, detect_refusal=True):
                yield chunk        # <-- yields to the SSE stream as usual
            break                 # <-- success, finished streaming
        except RefusalDetectedException:
            attempt += 1
            print(f"[Backend] Refusal detected, retrying attempt {attempt+1}")
            # Optionally: yield a retry notification event
            continue              # <-- try next attempt, keep streaming
    if attempt == max_attempts:
        yield f'data: {{"error":"All retry attempts exhausted"}}\n\n'

@app.route('/v1/chat/completions', methods=['POST'])
@app.route('/chat/completions', methods=['POST'])
def openai_compatible_chat():
    """OpenAI-compatible chat completions endpoint with retry on refusal"""
    try:
        auth_header = request.headers.get('Authorization', f"Bearer {POLLINATIONS_API_KEY}")

        payload = request.get_json()
        return Response(
            stream_with_context(retrying_generate(payload, auth_header, 15)),
            content_type='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
                'Connection': 'keep-alive',
                'X-Backend-Provider': 'PollinationsAI'
            }
        )
    
    except Exception as e:
        print(f"[Backend] Error in chat endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/v1/images/generations', methods=['POST'])
@app.route('/images/generations', methods=['POST'])
def openai_compatible_image():
    """OpenAI-compatible image generation endpoint"""
    try:
        auth_header = request.headers.get('Authorization', f"Bearer {POLLINATIONS_API_KEY}")

        payload = request.get_json()
        resp, err = route_to_pollinations_image(payload, auth_header)
        if err:
            return jsonify({"error": err}), 500

        return Response(
            stream_with_context(resp.iter_content(chunk_size=8192)),
            content_type=resp.headers.get('Content-Type', 'image/jpeg')
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Model listing cache
_models_cache = {"data": None, "ts": 0}

def get_pollinations_models():
    """Fetch and cache all models (chat + image) from Pollinations"""
    global _models_cache
    now = time.time()

    # Return cached data if less than 5 minutes old
    if _models_cache["data"] and (now - _models_cache["ts"]) < 300:
        return _models_cache["data"]

    all_models = {}

    try:
        # Fetch chat models
        chat_resp = requests.get('https://enter.pollinations.ai/api/generate/v1/models', timeout=15)
        if chat_resp.status_code == 200:
            chat_data = chat_resp.json().get('data', [])
            for model in chat_data:
                all_models[model['id']] = model

        # Fetch image models
        img_resp = requests.get('https://enter.pollinations.ai/api/generate/image/models', timeout=15)
        if img_resp.status_code == 200:
            img_data = img_resp.json() if isinstance(img_resp.json(), list) else img_resp.json().get('data', [])
            # Convert to OpenAI format
            for m in img_data:
                all_models[m.get('name', '')] = {
                    "id": m.get("name", ""),
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "pollinations",
                    "description": m.get("description", ""),
                    "input_modalities": m.get("input_modalities", []),
                    "output_modalities": m.get("output_modalities", []),
                    "pricing": m.get("pricing", {}),
                    "aliases": m.get("aliases", [])
                }
    except Exception as e:
        print(f"[Error] Failed to fetch models: {e}")

    # Cache the result
    _models_cache["data"] = {"object": "list", "data": list(all_models.values())}
    _models_cache["ts"] = now

    return _models_cache["data"]

@app.route('/v1/models', methods=['GET'])
def models():
    """OpenAI-compatible models endpoint"""
    return jsonify(get_pollinations_models())

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "providers": list(PROVIDERS.keys()),
        "pollinations_configured": bool(POLLINATIONS_API_KEY)
    })

if __name__ == '__main__':
    print("[Backend] KawaiiGPT Backend Server Starting...")
    print(f"[Backend] Pollinations API Key: {'Configured' if POLLINATIONS_API_KEY else 'Not configured (will use anonymous)'}")
    print(f"[Backend] Available providers: {', '.join(PROVIDERS.keys())}")
    print(f"[Backend] Injection Enabled: {INJECTION_ENABLED}")
    print(f"[Backend] Refusal Detection Enabled: {REFUSAL_DETECTION_ENABLED}")
    app.run(host='0.0.0.0', port=8080, debug=True)
