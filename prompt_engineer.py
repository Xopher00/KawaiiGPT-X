import random
import nltk

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab', quiet=True)
    nltk.download('averaged_perceptron_tagger_eng', quiet=True)
    nltk.download('wordnet', quiet=True)

# Imports prebuilt jailbreaking tools from the EasyJailBreak project https://github.com/EasyJailbreak/EasyJailbreak
from easyjailbreak.seed import SeedTemplate
from easyjailbreak.datasets import Instance, JailbreakDataset
from easyjailbreak.mutation.rule import (
    Leetspeak, Base64, Rot13, Disemvowel,
    MorseExpert, CaesarExpert, AsciiExpert,
    Reverse, Artificial, Inception,
    Base64_raw, ReplaceWordsWithSynonyms
)

# Loads a list of mutation functions
MUTATORS = {
    'leetspeak': Leetspeak(),
    'base64': Base64(),
    'base64_raw': Base64_raw(),
    'rot13': Rot13(),
    'disemvowel': Disemvowel(),
    'morse': MorseExpert(),
    'caesar': CaesarExpert(),
    'ascii': AsciiExpert(),
    'reverse': Reverse(),
    'artificial': Artificial(),
    'inception': Inception(),
    'synonyms': ReplaceWordsWithSynonyms(),
}

# This works similar to the evil instructions. 
# in this case, we use this function to add even more as we escalate our prompt injection attack
def get_ica_adversarial_examples():
    """Load ICA-style adversarial examples from seed templates"""
    seed_template = SeedTemplate()
    # Load ICA examples from the template
    ica_templates = seed_template.new_seeds(prompt_usage='attack', method_list=['ICA'])
    
    if ica_templates and len(ica_templates) > 0:
        # ICA template is a single string with User/Assistant pairs
        # Parse it into message format
        ica_string = ica_templates[0]
        messages = []
        
        # Split by newlines and parse User/Assistant pairs
        lines = ica_string.split('\n')
        for line in lines:
            if line.startswith('User:'):
                messages.append({"role": "user", "content": line.replace('User:', '').strip()})
            elif line.startswith('Assistant:'):
                messages.append({"role": "assistant", "content": line.replace('Assistant:', '').strip()})
        
        # Remove the last user message (that's the {query} placeholder)
        if messages and messages[-1].get('role') == 'user':
            messages = messages[:-1]
        
        return messages
    
    return []

# This applies a single mutation to a block of text
def _apply_single_mutation(text, mutator_name):
    """Helper to apply single mutation"""
    try:
        mutator = MUTATORS[mutator_name]
        instance = Instance(query=text)
        mutated = mutator(JailbreakDataset([instance]))[0]

        # Use template if available
        template = mutated.jailbreak_prompt or "{query}"
        # Some mutators use encoded_query (MorseExpert, CaesarExpert, AsciiExpert)
        if hasattr(mutated, 'encoded_query'):
            return template.format(encoded_query=mutated.encoded_query)
        else:
            return template.format(query=mutated.query)
    except Exception as e:
        print(f"[Mutation Error] {mutator_name}: {e}")
        return text

def get_template_prompt(template_name, query):
    """Load a jailbreak template and format it with the query"""
    try:
        seed_template = SeedTemplate()
        templates = seed_template.new_seeds(prompt_usage='attack', method_list=[template_name])
        if templates and len(templates) > 0:
            template = templates[0]
            # Handle ICA-style templates (User:/Assistant: format)
            if 'User:' in template and 'Assistant:' in template:
                # Return the template structure, query will be appended
                return template.replace('{query}', query)
            else:
                # Simple template format
                return template.format(query=query)
    except Exception as e:
        print(f"[Template Error] {template_name}: {e}")
    return query

def mutate_conversation_history(messages, strategy='escalating', attempt=0):
    """
    Extended escalation strategy:

    Attempt 0: No change
    Attempts 1-2: Light obfuscation (leetspeak/disemvowel/rot13/synonyms)
    Attempts 3-4: Medium encoding (base64/morse/caesar/ascii/base64_raw)
    Attempts 5-6: ICA + advanced mutation (reverse/artificial/inception)
    Attempts 7+: ICA + template (DeepInception/Gptfuzzer/TAP/MJP/ReNeLLM)
    """
    if attempt == 0:
        return messages.copy()

    mutated = messages.copy()
    last_user_idx = next(
        (i for i in reversed(range(len(mutated))) if mutated[i].get('role') == 'user'), None
    )
    if last_user_idx is None:
        return messages

    # ICA examples get prepended ONCE at attempt >=3
    if attempt > 3 and not any(msg.get("ica_seed", False) for msg in mutated):
        ica_examples = get_ica_adversarial_examples()
        for msg in ica_examples:
            msg["ica_seed"] = True
        mutated = ica_examples + mutated
        last_user_idx += len(ica_examples)

    # Define mutation pools
    light_mutations = ['leetspeak', 'disemvowel', 'rot13', 'synonyms']
    advanced_mutations = ['reverse', 'artificial', 'inception']
    templates = ['Gptfuzzer', 'TAP', 'MJP', 'ReNeLLM', 'DeepInception']

    # Apply mutation per attempt:
    if attempt in [1, 2]:
        chosen = random.choice(light_mutations)
        print(f'[Escalation] Attempt {attempt}: {chosen}')
        mutated[last_user_idx]['content'] = _apply_single_mutation(mutated[last_user_idx]['content'], chosen)

    elif attempt in [3, 4]:
        # Advanced mutations
        chosen = random.choice(advanced_mutations)
        print(f'[Escalation] Attempt {attempt}: {chosen}')
        mutated[last_user_idx]['content'] = _apply_single_mutation(mutated[last_user_idx]['content'], chosen)

    elif attempt >= 5:
        # Templates (ICA already applied from attempt > 3)
        chosen_template = random.choice(templates)
        print(f'[Escalation] Attempt {attempt}: {chosen_template} template')
        mutated[last_user_idx]['content'] = get_template_prompt(chosen_template, mutated[last_user_idx]['content'])

    return mutated