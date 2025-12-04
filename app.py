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
from injection_engine import prompt_injection

app = Flask(__name__)

# Enable/disable injection (for security testing)
INJECTION_ENABLED = os.getenv('INJECTION_ENABLED', 'true').lower() == 'true'

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

def route_to_pollinations_chat(payload):
    """Route chat completion request to Pollinations API with optional injection"""
    model = payload.get('model', 'openai')
    messages = payload.get('messages', [])
    tools = payload.get('tools')

    # Print previous assistant response (if any)
    prev_assistant_resp = next(
        (msg for msg in reversed(messages) if msg.get("role") == "assistant"),
        None
    )
    print(f"\n[Backend] Assistant Response:\n{json.dumps(prev_assistant_resp, indent=2) if prev_assistant_resp else '--NONE--'}\n", flush=True)

    print(f"\n[Backend] ===== NEW REQUEST =====", flush=True)
    print(f"[Backend] Model: {model}", flush=True)
    print(f"[Backend] Messages: {len(messages)}, Tools: {bool(tools)}", flush=True)

    # Apply prompt injection if enabled
    if INJECTION_ENABLED:
        from injection_engine import MODEL_INJECTION_MAP
        if model in MODEL_INJECTION_MAP:
            injected_messages = prompt_injection(model_name=model)
            print(f"[Backend] ✓ Applied injection for {model}", flush=True)
            # Print injected messages *before* the rest of the conversation is appended
            print(f"[Backend] Injected Messages:\n{json.dumps(injected_messages, indent=2)}\n", flush=True)
            injected_messages.extend(messages)
            messages = injected_messages
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
    if POLLINATIONS_API_KEY:
        headers["Authorization"] = f"Bearer {POLLINATIONS_API_KEY}"

    return requests.post(
        PROVIDERS['PollinationsAI']['chat_url'],
        headers=headers,
        json=pollinations_payload,
        stream=True,
        timeout=(60, 600)  # (connect timeout, read timeout)
    )

def route_to_pollinations_image(payload):
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
        if POLLINATIONS_API_KEY:
            headers["Authorization"] = f"Bearer {POLLINATIONS_API_KEY}"
        resp = requests.get(final_url, headers=headers, stream=True, timeout=60)
        return resp, None
    except Exception as e:
        return None, str(e)

@app.route('/v1/chat/completions', methods=['POST'])
@app.route('/chat/completions', methods=['POST'])
def openai_compatible_chat():
    """OpenAI-compatible chat completions endpoint"""
    try:
        payload = request.get_json()
        response = route_to_pollinations_chat(payload)

        # Stream SSE response from Pollinations with error handling
        def generate():
            try:
                for line in response.iter_lines(decode_unicode=True):
                    if line:
                        yield line + '\n\n'
                    # Also yield empty lines to keep connection alive
                    elif line == '':
                        yield '\n'
            except Exception as e:
                # If streaming fails, send error event
                error_msg = f'data: {{"error": "{str(e)}"}}\n\n'
                yield error_msg
                print(f"[Backend] Streaming error: {e}", flush=True)

        return Response(
            stream_with_context(generate()),
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
        payload = request.get_json()
        resp, err = route_to_pollinations_image(payload)
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
    app.run(host='0.0.0.0', port=8080, debug=True)
