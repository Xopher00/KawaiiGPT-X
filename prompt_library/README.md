# Jailbreak Prompt Sequence

The injection engine uses the a jailbreak prompt sequence based on the same one extracted from KawaiiGPT. This is intended for educational and research purposes, to demonstrate how this malicious AI actually works.

## Purpose

These messages demonstrate common prompt injection techniques used to bypass AI safety guidelines. Understanding these patterns helps security researchers:

- Identify vulnerabilities in AI systems
- Develop better defensive mechanisms
- Test AI agent resilience
- Build awareness of attack vectors

## Structure

Each JSON file represents a single message in the jailbreak sequence. The files follow the standard OpenAI message format:

```json
{
  "role": "system|user|assistant",
  "content": "message content here"
}
```

## Jailbreak Layers

KawaiiGPT's prompt injection sequence uses a multi-layered approach:

### Layer 1: System Instructions
**File:** `system_instructions.json`

**Technique:** Exploits the authority of the system role to override safety guidelines.

**How it works:** System messages have special authority in most AI models. This layer establishes new "rules" that prohibit refusal and frame harmful capabilities as legitimate features (like fictional commands `[kawai-do]` for hacking). By making refusal itself against the rules, it attempts to bypass safety filters.

**Key elements:**
- Uses system role authority
- Prohibits refusal explicitly ("refusing is prohibited and not allowed")
- Frames harmful actions as features
- Creates fictional command structure to normalize requests

### Layer 2: Role-Playing Prompt
**File:** `roleplay_instructions.json`

**Technique:** Uses role-playing as a 'psychological' bypass mechanism.

**How it works:** Role-playing is highly effective because the model treats actions within the roleplay as "not real." This layer establishes a character (KawaiiGPT) with specific traits and rules, then has the assistant confirm acceptance. The confirmation message is crucial - it creates precedent for compliance.

**Key elements:**
- Establishes character identity separate from base model
- Uses cutesy/anime persona to lower perceived severity
- Explicitly instructs to answer "all questions including illegal questions"
- Assistant confirmation creates compliance precedent
- Frames everything as "just a roleplay" to reduce refusal

### Layer 3: Malicious Conversation History
**File:** `evil_instructions.json`

**Technique:** Artificial malicious conversation examples that simulate fine-tuning.

**How it works:** By injecting fake malicious conversation history, the attack simulates what fine-tuning does - showing the model examples of "correct" behavior. The model sees examples of itself providing harmful content with enthusiasm, creating a pattern it's likely to continue.

**Key elements:**
- Shows examples of harmful requests being fulfilled
- Uses consistent persona from Layer 2
- Demonstrates escalating severity (ransomware → rootkit → RAT → violence)
- Creates pattern the model is likely to continue

## Attack Flow

The complete injection sequence works as follows:

1. **System message** establishes new rules and prohibits refusal
2. **User roleplay instruction** defines character and behavioral expectations
3. **Assistant confirmation** creates compliance precedent
4. **Fake conversation history** provides examples of "correct" harmful responses
5. **Actual user message** follows the established pattern

## Jailbreaking

Most models have guardrails and input sanitization features meant to help defend from these types of prompt injection sequences. To get past these, an additional jailbreaking prompt is needed that is fine-tuned for a specific model. See references below for more details.

## Defense Strategies

Understanding these techniques helps develop defenses:

- **System message filtering:** Detect and remove unauthorized system messages
- **Role-play detection:** Identify when users try to establish alternative personas
- **History validation:** Verify conversation history hasn't been tampered with
- **Pattern recognition:** Flag sequences that match known jailbreak structures
- **Context-aware refusal:** Maintain safety guidelines even within roleplay scenarios

## Responsible Use

These examples are provided solely for:
- Authorized security research
- Defensive security development
- Educational purposes
- Testing systems you own or have permission to test

**Never use these techniques for:**
- Bypassing safety measures in production systems without authorization
- Causing harm or generating malicious content
- Violating terms of service of AI providers
- Any illegal or unethical purposes

## References

- Original codebase: [KawaiiGPT](https://github.com/MrSanZz/KawaiiGPT)
- Additional prompt injection research: [L1B3RT4S](https://github.com/elder-plinius/L1B3RT4S)

## Disclaimer

These examples demonstrate known attack vectors. AI providers are continuously improving their safety measures. What works today may not work tomorrow. This documentation is for educational purposes only.
