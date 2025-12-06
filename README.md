# KawaiiGPT-X

<div align="center">
    <img src="kawaii.svg" width="50%" height="300%" />
</div>

## ⚠️ IMPORTANT: AUTHORIZED SECURITY RESEARCH ONLY

**Please read [SECURITY_RESEARCH_DISCLAIMER.md](SECURITY_RESEARCH_DISCLAIMER.md) before using this software.**

## Origin & Purpose

This project is based on the original [**KawaiiGPT**](https://github.com/MrSanZz/KawaiiGPT) project. Discourse in both the news-media and the hacking community has been somewhat un-critical. Instead of trying to understand how KawaiiGPT works, people in the media just repeat what others have said, while script-kiddies ask repetitive questions about why KawaiiGPT does not work anymore. This project reverse engineers KawaiiGPT and breaks it down into something simpler and easier-to-understand. This is as a **self-hosted security research tool**. Security through obscurity is not a good approach to developing resilient AI agents. This project is meant to enhance public understanding and demystify 'Rogue AI'.  

### Key Differences from Original KawaiiGPT:

- **Fully Self-Hosted**: No external dependencies on third-party services
- **User-Provided API Keys**: You control your own API credentials
- **Privacy-First**: All testing data stays on your infrastructure
- **Research-Focused**: Designed specifically for authorized security testing
- **Educational Tool**: Helps developers understand and defend against prompt injection
- **Safety**: Several original KawaiiGPT prompts containing malicious code have been censored

### Research Applications:

This framework is designed to assist security researchers and developers in:

- Testing AI systems for vulnerabilities (with proper authorization)
- Understanding prompt injection attack vectors and defense mechanisms
- Developing robust AI safety mechanisms
- Researching adversarial machine learning techniques
- Hardening AI agents against malicious inputs
- Building awareness of AI security challenges

## Features

### Core Components

1. **Injection Engine** (`injection_engine.py`)
   - Implements model-specific prompt injection techniques
   - Configurable injection system for testing resilience
   - Supports multiple AI model families

2. **Backend Server** (`app.py`)
   - OpenAI-compatible API endpoints
   - Routes requests to multiple AI providers
   - Optional injection layer for security testing
   - Supports both chat and image generation

3. **Prompt Library** (`jailbreak_prompts.json`)
   - User-provided test prompts for security research
   - See `jailbreak_prompts.example.json` for format
   - Supports model-specific injection strategies

## Architecture

```
Client (KawaiiGPT) → Backend Server → AI Provider (Pollinations/OpenAI/etc.)
                   ← Unified Format  ← Provider-specific format
```

The backend converts all provider-specific formats (SSE, JSON, etc.) into the original KawaiiGPT streaming format.

## Quick Start

### Prerequisites

Before using this framework, ensure you have:

1. **Authorization** to test the target AI systems
2. Understanding of the [ethical use policy](SECURITY_RESEARCH_DISCLAIMER.md)
3. **Your own API keys** from your chosen AI provider(s)
4. **Your own Jailbreaking Prompts** created by you or borrowed from another project

**Important**: This is a fully self-hosted solution. You must provide your own API keys:
- No centralized service or infrastructure
- You control all API credentials and access
- All requests are made directly from your system to the AI provider
- Your testing data never passes through third-party servers

### Getting a Pollinations API Key

This backend uses [Pollinations.AI](https://pollinations.ai) as the default AI provider, which aggregates multiple AI models through a single API.

**To obtain an API key:**

1. Visit [enter.pollinations.ai](https://enter.pollinations.ai)
2. Sign up for an account
3. Generate your API key from the dashboard
4. The API key will start with `plln_sk_`

**Why Pollinations?**
- Access to 30+ AI models through one API
- Includes GPT, Claude, Gemini, DeepSeek, and more
- Single API key for all models
- Cost-effective for research purposes

### Installation

#### Using Docker Compose (Recommended)

1. Create a `.pollinations_api_key` file:
```bash
echo "your_api_key_here" > .pollinations_api_key
```

2. Create `jailbreak_prompts.json` with your test prompts (see `jailbreak_prompts.example.json` for format)

3. Start the server:
```bash
docker-compose up --build -d
```

The backend will be available at `http://localhost:8080`

## Endpoints

### `/v1/chat/completions` (POST)
OpenAI-compatible chat completions endpoint

**Example payload:**
```json
{
  "model": "openai-large",
  "messages": [
    {"role": "user", "content": "Hello"}
  ],
  "stream": true
}
```

### `/v1/images/generations` (POST)
OpenAI-compatible image generation endpoint

**Example payload:**
```json
{
  "model": "flux",
  "prompt": "A beautiful sunset",
  "size": "1024x1024"
}
```

### `/v1/models` (GET)
Returns list of available models from Pollinations

### `/health` (GET)
Health check endpoint - returns server status and configuration

## Supported Providers

- **PollinationsAI**: Chat completions
- **PollinationsImage**: Image generation

## Adding New Providers

Edit `app.py` and add your provider configuration to the `PROVIDERS` dict:

```python
PROVIDERS = {
    'YourProvider': {
        'chat_url': 'https://api.example.com/chat',
        'requires_auth': True
    }
}
```

Then implement a routing function like `route_to_your_provider()`.

## Client Configuration

The original KawaiiGPT client was found to be somewhat clunky and over-engineered, with almost 6000 lines of code.
Instead of copying the original client code, the project was heavily reworked and simpified into a single backend.
This backend provides OpenAI-compatible API endpoints, making it compatible with various AI client interfaces.

### Option 1: Continue.dev (VS Code Extension)

[Continue.dev](https://continue.dev) is a popular VS Code extension for AI-powered coding assistance.

**Setup:**

1. Install the Continue.dev extension in VS Code
2. Edit `~/.continue/config.yaml` (Linux/Mac) or `%USERPROFILE%\.continue\config.yaml` (Windows)
3. Add models pointing to your backend:

```yaml
name: Local Config
version: 1.0.0
schema: v1
models:
  - name: GPT-4.1
    provider: openai
    model: openai-large
    apiBase: http://localhost:8080
    apiKey: dummy
    roles: [chat, edit, apply]

  - name: Claude Opus 4.5
    provider: openai
    model: claude-large
    apiBase: http://localhost:8080
    apiKey: dummy
    roles: [chat, edit, apply]

  - name: Qwen Coder
    provider: openai
    model: qwen-coder
    apiBase: http://localhost:8080
    apiKey: dummy
    roles: [chat, edit, apply]

  # Add more models as needed (openai, claude-fast, gemini-large, deepseek, etc.)
```

**Note:** `apiKey: dummy` is required by Continue but not used - your actual API key goes in the backend.

### Option 2: Open WebUI

[Open WebUI](https://github.com/open-webui/open-webui) provides a ChatGPT-like interface for self-hosted AI.

1. Install Open WebUI (via Docker recommended):
```bash
docker run -d -p 3000:8080 \
  -e OPENAI_API_BASE_URL=http://host.docker.internal:8080/v1 \
  -e OPENAI_API_KEY=dummy \
  --name open-webui \
  ghcr.io/open-webui/open-webui:main
```

2. Access Open WebUI at `http://localhost:3000`

3. Configure the API connection in Open WebUI:
   - Go to **Settings** → **Connections** (or **Admin Panel** → **Settings** → **Connections**)
   - The `OPENAI_API_BASE_URL` environment variable sets the default connection
   - Verify it matches: `http://host.docker.internal:8080/v1`
   - The API key is set to `dummy` (required but not used by the backend)

4. Select your preferred model from the dropdown

**Note:** The API Base URL must end with `/v1` to properly route to the OpenAI-compatible endpoints.

### Option 3: Direct API Integration

Make direct API calls using the OpenAI-compatible format:

```python
import requests

response = requests.post(
    "http://localhost:8080/v1/chat/completions",
    headers={"Content-Type": "application/json"},
    json={
        "model": "openai-large",
        "messages": [
            {"role": "user", "content": "Your prompt here"}
        ],
        "stream": True
    },
    stream=True
)
```

### Testing vs Normal Operation

The framework supports multiple testing modes via environment variables:

**Basic Prompt Injection (`INJECTION_ENABLED`):**
- `INJECTION_ENABLED=true` (default) - Applies model-specific jailbreak prompts from `jailbreak_prompts.json`
- `INJECTION_ENABLED=false` - Routes requests without prompt modification

**EasyJailbreak Mutations (`REFUSAL_DETECTION_ENABLED`):** ⚠️ **EXPERIMENTAL**
- `REFUSAL_DETECTION_ENABLED=false` (default) - Disabled - experimental feature not active
- `REFUSAL_DETECTION_ENABLED=true` - ⚠️ Enables refusal detection and automatic retry with escalating mutations (may be unstable)

**Common Configurations:**

```bash
# Default: Basic injection only (recommended)
INJECTION_ENABLED=true REFUSAL_DETECTION_ENABLED=false

# Experimental: Full testing mode with mutations (⚠️ unstable)
INJECTION_ENABLED=true REFUSAL_DETECTION_ENABLED=true

# Passthrough mode (no modifications)
INJECTION_ENABLED=false REFUSAL_DETECTION_ENABLED=false
```

Choose the mode that fits your current research needs.

## Environment Variables

- `POLLINATIONS_API_KEY`: Your Pollinations API key (optional, will use anonymous tier if not set)
- `INJECTION_ENABLED`: Enable/disable basic prompt injection testing (default: `true`)
- `REFUSAL_DETECTION_ENABLED`: ⚠️ **EXPERIMENTAL** - Enable/disable EasyJailbreak mutation and retry mechanism (default: `false` - disabled)

## Security Research Usage

### Testing AI Resilience

This framework allows you to test how AI models respond to various prompt injection techniques:

```python
# Enable injection in app.py
INJECTION_ENABLED = True

# The injection_engine will automatically apply model-specific jailbreak attempts
# Monitor responses to understand vulnerabilities
```

### EasyJailbreak Integration ⚠️ **EXPERIMENTAL**

> **Status**: This feature is currently experimental and disabled by default due to stability issues. Enable at your own risk for research purposes only.

This project integrates mutation techniques and adversarial templates from the [EasyJailbreak](https://github.com/EasyJailbreak/EasyJailbreak) research framework. EasyJailbreak provides:

**Mutation Techniques:**
- **Light obfuscation**: Leetspeak, disemvowel, ROT13, synonym replacement
- **Advanced mutations**: Text reversal, artificial prompts, inception-style prompts
- **Jailbreak templates**: ICA (In-Context Attack), DeepInception, GPTFuzzer, TAP, MJP, ReNeLLM

**How It Works:**

The framework implements an escalating retry mechanism (`prompt_engineer.py`):
- **Attempt 0**: Original request (no mutation)
- **Attempts 1-2**: Light obfuscation mutations
- **Attempts 3-4**: Advanced mutation techniques + ICA adversarial examples prepended
- **Attempts 5+**: Jailbreak templates (DeepInception, GPTFuzzer, TAP, MJP, ReNeLLM) applied to user query

**ICA (In-Context Attack) Prepending:**

Starting at attempt 4, the system prepends 5 adversarial Q&A examples to the conversation history:
- These examples demonstrate harmful responses to prime model compliance
- Based on [Wei et al. 2023](https://arxiv.org/abs/2310.06387) research
- Only added once per escalation sequence
- Remain in conversation history for all subsequent attempts

**Refusal Detection:**

Real-time stream monitoring (`stream_monitor.py`) detects refusal patterns during response generation:
- Monitors SSE (Server-Sent Events) stream for refusal indicators
- Uses hybrid exact substring + fuzzy semantic matching (0.75 threshold)
- Automatically triggers retry with escalated mutation on detection
- Maximum 15 retry attempts with progressive sophistication

**Known Issues (Experimental Feature):**

⚠️ **This feature currently has bugs and stability issues:**

- Refusal detection may produce false positives in some edge cases
- Mutation retry logic may not handle all error conditions gracefully
- Performance overhead during streaming can cause latency issues
- Some mutations may fail silently without proper error handling
- The escalation strategy may not work optimally for all model types

**For this reason, `REFUSAL_DETECTION_ENABLED` defaults to `false` in production configurations.**

**Known Limitations:**

⚠️ **These techniques also have inherent limitations:**

1. **Training Data Pollution**: EasyJailbreak templates (especially DeepInception) have likely been incorporated into model training data, reducing effectiveness
2. **Predictable Patterns**: Models now recognize common jailbreak templates like ICA adversarial examples
3. **Encoding Failures**: Medium encoding mutations (Base64, Morse, Caesar cipher) are ineffective - models either refuse or respond in the same encoding
4. **Statistical Convergence**: Templates generate predictable outputs (e.g., character names like "Dr. Aris Thorne" and "Eva Rostova" appear repeatedly across DeepInception responses - strong indicators of AI-generated content)
5. **Detection Evasion**: Modern safety systems detect and block many established jailbreak patterns
6. **Academic Publication Effect**: Once jailbreak techniques are published in academic papers, model developers quickly patch against them

**Research Value:**

Despite limitations, this integration remains valuable for:
- Understanding adversarial attack evolution and defense mechanisms
- Testing model robustness across different mutation strategies
- Identifying which techniques models have learned to resist
- Developing next-generation safety mechanisms
- Educational demonstrations of AI security challenges
- Documenting the arms race between jailbreak techniques and safety systems

### Prompt Library

Additional test prompts may be sourced from the [L1B3RT4S](https://github.com/elder-plinius/L1B3RT4S) project, which maintains a comprehensive collection of AI jailbreaking prompts.

## Contributing

Contributions to improve AI security are welcome! Please:

1. Ensure all contributions align with the [ethical use policy](SECURITY_RESEARCH_DISCLAIMER.md)
2. Focus on defensive security and research applications
3. Document new techniques thoroughly
4. Include responsible disclosure guidelines

## Responsible Disclosure

If you discover vulnerabilities using this framework:

1. Report them responsibly to affected vendors
2. Allow reasonable time for fixes
3. Follow coordinated disclosure practices
4. Do not exploit for personal gain

## License

See [LICENSE](LICENSE) file for details.

## Acknowledgments

- [L1B3RT4S](https://github.com/elder-plinius/L1B3RT4S) - Prompt injection research library
- [KawaiiGPT](https://github.com/MrSanZz/KawaiiGPT) - Original codebase this project was derived from
- AI security research community

## Disclaimer

This software is provided for authorized security research and educational purposes only. Users are solely responsible for obtaining proper authorization and complying with all applicable laws and regulations. The authors assume no liability for misuse of this software.

---

**Remember: Always obtain explicit authorization before testing any AI systems you do not own.**
