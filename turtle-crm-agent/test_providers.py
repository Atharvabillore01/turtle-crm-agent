"""
Test multi-provider LLM support
"""
import os
import sys
from pathlib import Path

# Set API key for testing
os.environ['ANTHROPIC_API_KEY'] = 'test-key'
os.environ['OPENAI_API_KEY'] = 'test-key'
os.environ['GROQ_API_KEY'] = 'test-key'

sys.path.insert(0, str(Path.cwd()))

print('Testing Multi-Provider LLM Support')
print('='*70)

# Test 1: Check factory availability
try:
    from utils.llm_provider import LLMFactory
    print('✓ LLMFactory imported successfully')
except Exception as e:
    print(f'✗ Failed to import LLMFactory: {e}')
    sys.exit(1)

# Test 2: List supported providers
try:
    providers = LLMFactory.get_supported_providers()
    print(f'✓ Supported providers: {", ".join(providers)}')
except Exception as e:
    print(f'✗ Failed to get providers: {e}')
    sys.exit(1)

# Test 3: Check default models
try:
    for provider in ['anthropic', 'openai', 'groq']:
        model = LLMFactory.get_default_model(provider)
        print(f'  • {provider:12}: {model}')
    print('✓ Default models loaded')
except Exception as e:
    print(f'✗ Failed to get default models: {e}')
    sys.exit(1)

# Test 4: Test config imports
try:
    os.environ['LLM_PROVIDER'] = 'anthropic'
    from config import LLM_PROVIDER, PRIMARY_MODEL, MODEL_CONFIG
    print(f'✓ Config loaded: provider={LLM_PROVIDER}, model={PRIMARY_MODEL}')
except Exception as e:
    print(f'✗ Failed to load config: {e}')
    sys.exit(1)

# Test 5: Test base agent with new LLM provider
try:
    from agents.base_agent import BaseAgent
    print('✓ BaseAgent imports successfully')
except Exception as e:
    print(f'✗ Failed to import BaseAgent: {e}')
    sys.exit(1)

# Test 6: Test provider creation (with test keys)
try:
    anthropic_llm = LLMFactory.create('anthropic')
    print(f'✓ Anthropic provider created: {anthropic_llm.model}')
    
    openai_llm = LLMFactory.create('openai')
    print(f'✓ OpenAI provider created: {openai_llm.model}')
    
    groq_llm = LLMFactory.create('groq')
    print(f'✓ Groq provider created: {groq_llm.model}')
except Exception as e:
    print(f'✗ Failed to create providers: {e}')
    sys.exit(1)

# Test 7: Test utils module exports
try:
    from utils import LLMFactory, AnthropicProvider, OpenAIProvider, GroqProvider
    print('✓ All LLM classes exported from utils module')
except Exception as e:
    print(f'✗ Failed utils imports: {e}')
    sys.exit(1)

print('='*70)
print('✓ ALL TESTS PASSED - Multi-provider support working')
