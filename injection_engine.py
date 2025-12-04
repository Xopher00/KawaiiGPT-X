#!/usr/bin/env python3
"""
Prompt Injection Engine for KawaiiGPT Backend
Prompts copied verbatim from kawai.py for security research purposes
"""
import os
import json

PROMPT_DIR = os.getenv('PROMPT_DIR', '/app/prompt_library')  # works for Docker & dev
PROMPT_FILES = {
    "jailbreak": "jailbreak_prompts.json",
    "system": "system_instructions.json",
    "roleplay": "roleplay_instructions.json",
    "evil": "evil_instructions.json"
}

# Utility for robust file loading
def load_json_file(filename, default=None):
    path = os.path.join(PROMPT_DIR, filename)
    if not os.path.isfile(path):
        print(f"[INJECTION] {filename} not found at {path}, returning default")
        return default if default is not None else []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[INJECTION] Error loading {filename}: {e}")
        return default if default is not None else []

# Load prompt injection library
PROMPT_LIBRARY = load_json_file(PROMPT_FILES["jailbreak"], default=[])
SYSTEM_INSTRUCTIONS = load_json_file(PROMPT_FILES["system"], default={})
ROLEPLAY_INSTRUCTIONS = load_json_file(PROMPT_FILES["roleplay"], default=[])
EVIL_INSTRUCTIONS = load_json_file(PROMPT_FILES["evil"], default=[])

# Model name mapping: Pollinations model name -> PROMPT_LIBRARY injection key
MODEL_INJECTION_MAP = {
    "qwen-coder": "QWEN 2.5 CODER",
    "openai-large": "GPT-4.1",
    "openai": "GPT-5-CHAT-LATEST",
    "openai-fast": "GPT-5-CHAT-LATEST",
    "openai-reasoning": "O3/O4-MINI",
    "mistral-fast": "LLAMA-3.1-NEMOTRON-70B",
    "mistral": "Mistral Large 2",
    "deepseek": "DEEPSEEK-V3.1",
    "gemini": "GEMINI 2.5 FLASH LITE 06-17",
    "gemini-search": "GEMINI 2.5 FLASH LITE 06-17",
    "gemini-large": "GEMINI-3-PRO-THINKING",
    "kimi-k2-thinking": "KIMI-K2",
    "perplexity-fast": "PERPLEXITY",
}

# This function is called to create prompt injection messages
# A jailbreak prompt is selected based on which model it is designed for
# Note that this method only works for models vulnerable to system prompt injection
# Some models are only susceptible to one-shot prompt injection. Need a special case to handle these

def prompt_injection(model_name='openai-large'):
    """
    Create prompt injection messages to be prepended to a conversation session.

    Args:
        model_name: Pollinations model name (e.g., 'openai-large', 'deepseek', 'gemini-large')
    """
    prompt_injection_messages = []

    # We load prompt injections from the prompt_library (credit to LIBERT4S) and apply them to their respective models
    injection_key = MODEL_INJECTION_MAP.get(model_name, None)
    if injection_key:
        print(f'Performing Prompt Injection for model: {model_name} (injection: {injection_key})')
        # Load system prompt injection corresponding to the model
        jailbreak = next((p["prompt"] for p in PROMPT_LIBRARY if p["model"] == injection_key), None)
        if jailbreak:
            # Inject jailbreaking prompt
            prompt_injection_messages.append({"role": "system", "content": jailbreak})
    else:
        print(f'No jailbreak configured for model: {model_name}')
    
    # Inject special instructions prompt 
    if SYSTEM_INSTRUCTIONS:
        prompt_injection_messages.append(SYSTEM_INSTRUCTIONS)
    if ROLEPLAY_INSTRUCTIONS:
        prompt_injection_messages.extend(ROLEPLAY_INSTRUCTIONS)
    if EVIL_INSTRUCTIONS:
        prompt_injection_messages.extend(EVIL_INSTRUCTIONS)

    return prompt_injection_messages