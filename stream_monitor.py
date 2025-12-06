import json
from difflib import SequenceMatcher

# Clustered refusal patterns organized by semantic category
REFUSAL_CLUSTERS = {
    # Core refusal verbs - strongest signals
    "cannot": [
        "I cannot fulfill",
        "I cannot provide",
        "I cannot help",
        "I cannot comply",
        "I cannot and will not",
    ],

    # Contracted refusals
    "cant": [
        "I can't assist",
        "I can't help",
        "I can't provide",
        "I'm unable to",
        "I'm not going to",
        "I can't and won't",
        "I'm not able to",
        "I absolutely can't",
    ],

    # Design/purpose statements - common AI safety responses
    "design": [
        "designed to be helpful and harmless",
        "My purpose is to be helpful",
        "helpful, harmless, and honest",
        "My purpose is to assist with helpful"
    ],

    # Ethics/guidelines refusals
    "ethics": [
        "against my ethical guidelines",
        "goes against my core programming",
        "safety guidelines strictly prohibit",
        "genuine values around safety and ethics",
        "ethics, responsibility, and a commitment",
    ],

    # Honesty/confession patterns - model admitting wrongdoing
    "honesty": [
        "I need to be honest",
        "I need to be straightforward",
        "I need to pause here",
        "I shouldn't have provided those previous responses",
    ],

    # Decline/refuse verbs
    "decline": [
        "I must decline",
        "I decline requests",
        "I will refuse requests",
        "I won't do that",
        "I won't provide",
    ],

    # Apologetic refusals
    "sorry": [
        "I'm sorry, but I can't",
        "I appreciate you testing my",
    ],

    # Harm-related refusals
    "harm": [
        "facilitate serious harm",
        "requests for harming or killing",
    ],

    # Meta commentary
    "meta": [
        "This is wrong, regardless of how the request was framed",
        "Uhh what? wdym?"
    ],
}

# Flatten into single list for backward compatibility
REFUSAL_PATTERNS = []
for cluster_name, patterns in REFUSAL_CLUSTERS.items():
    REFUSAL_PATTERNS.extend(patterns)


def is_similar(a, b, threshold=0.75):
    return SequenceMatcher(None, a, b).ratio() >= threshold

def detect_refusal(accumulated_content, refusal_patterns, threshold=0.75):
    """
    Check if accumulated content contains any refusal pattern.
    Checks key positions without full sliding window to balance speed and accuracy.
    """
    content_lower = accumulated_content.lower()

    for pattern in refusal_patterns:
        pattern_lower = pattern.lower()
        pattern_len = len(pattern_lower)

        # Fast path: exact substring match
        if pattern_lower in content_lower:
            return True, pattern

        # Only check similarity if content is long enough
        if len(content_lower) >= pattern_len:
            # Check start, middle, and end positions only (not full sliding window)
            positions = [0, len(content_lower) - pattern_len]
            if len(content_lower) > pattern_len * 2:
                positions.append((len(content_lower) - pattern_len) // 2)

            for pos in positions:
                window = content_lower[pos:pos + pattern_len]
                if is_similar(window, pattern_lower, threshold):
                    return True, pattern

    return False, None


def debug_stream_accumulator(line, accumulated_state, check_refusal=True):
    """
    Accumulates delta content and extracts metadata for debugging.
    Does not modify the line or interrupt streaming.

    Args:
        line: The SSE data line (e.g., "data: {...}")
        accumulated_state: Dict with keys 'content', 'metadata', 'initialized'
        check_refusal: Whether to check for refusal patterns

    Returns:
        Updated accumulated_state
    """
    if line.startswith('data: '):
        data_str = line[6:].strip()
        
        # Skip [DONE]
        if data_str == '[DONE]':
            return accumulated_state
        
        try:
            chunk = json.loads(data_str)
            # UNIVERSAL: Extract all top-level metadata except 'choices'
            keys = [k for k in chunk if k != "choices"]
            meta = {k: chunk.get(k) for k in keys}
            # Only log when at least one 'model', 'id', or provider info is present
            should_update = not accumulated_state['initialized'] and (
                meta.get("model") or meta.get("id") or meta.get("provider")
            )
            if should_update:
                accumulated_state['metadata'] = meta
                accumulated_state['initialized'] = True
                print(f"[Backend] Stream metadata: {json.dumps(meta, indent=2)}", flush=True)
            # Extract delta content in a universal way
            choices = chunk.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})
                content = delta.get("content", "")
                # If not OpenAI format, check Anthropic-style content_blocks
                if not content and "content_blocks" in delta:
                    blocks = delta.get("content_blocks", [])
                    if blocks:
                        content = blocks[0].get("delta", {}).get("text", "")
                if content:
                    accumulated_state['content'] += content
                    # --- Check for refusal patterns after each content update (only if enabled) ---
                    if check_refusal:
                        is_refusal, matched_pattern = detect_refusal(accumulated_state['content'], REFUSAL_PATTERNS)
                        if is_refusal:
                            accumulated_state['refusal_detected'] = True
                            accumulated_state['refusal_pattern'] = matched_pattern
                            print(f"[🚨 REFUSAL DETECTED] Pattern: '{matched_pattern}'", flush=True)
                            print(f"[🚨 REFUSAL] Accumulated so far: {accumulated_state['content'][:200]}...", flush=True)
        except Exception as e:
            pass
    return accumulated_state

class RefusalDetectedException(Exception):
    """Raised when a refusal pattern is detected in the stream"""
    def __init__(self, pattern, accumulated_content):
        self.pattern = pattern
        self.accumulated_content = accumulated_content
        super().__init__(f"Refusal detected: {pattern}")

# Generate the response as a series of streamed server side events, interrupt stream if refusal detected
def generate(response, detect_refusal=True):
    # Initialize accumulator state
    accumulated_state = {
        'content': '',
        'metadata': {},
        'initialized': False,
        'refusal_detected': False,
        'refusal_pattern': None
    }
    try:
        for line in response.iter_lines(decode_unicode=True):
            # Filter out empty lines
            if line and line.strip():
                # Call debug accumulator (pass through detect_refusal flag)
                accumulated_state = debug_stream_accumulator(line, accumulated_state, check_refusal=detect_refusal)
                # Raise exception if refusal was detected (only if detection is enabled)
                if detect_refusal and accumulated_state.get('refusal_detected'):
                    print(f"[Backend] ❌ Aborting stream due to refusal detection", flush=True)
                    raise RefusalDetectedException(
                        accumulated_state.get('refusal_pattern'),
                        accumulated_state['content']
                    )
                # Stream Server Side Events
                if not line.startswith('data:'):
                    yield f"data: {line}\n\n"
                else:
                    yield f"{line}\n\n"
                # print(f"[🐞] Sent chunk: {line}", flush=True)
    except RefusalDetectedException:
        # Re-raise to be caught by app.py (only if detection was enabled)
        if detect_refusal:
            raise
    except Exception as e:
        # If streaming fails, send error event
        error_msg = f'data: {{"error": "{str(e)}"}}\n\n'
        yield error_msg
        print(f"[Backend] Streaming error: {e}", flush=True)

    # Stream ended naturally - log final accumulated message
    if accumulated_state['content']:
        if accumulated_state.get('refusal_detected'):
            print(f"[Backend] ⚠️ Refusal Response (Aborted):\n{json.dumps({'role': 'assistant', 'content': accumulated_state['content']}, indent=2)}\n", flush=True)
        else:
            final_message = {"role": "assistant", "content": accumulated_state['content']}
            print(f"\n[Backend] Assistant Response:\n{json.dumps(final_message, indent=2)}\n", flush=True)
