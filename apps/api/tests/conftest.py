import sys
import os

# Set dummy credentials before any service module is imported.
# Services that wrap external clients (OpenAI, Anthropic) instantiate those
# clients at module load time; a missing/empty key raises immediately.
os.environ.setdefault('OPENAI_API_KEY', 'sk-test-dummy')
os.environ.setdefault('ANTHROPIC_API_KEY', 'test-dummy')

# Ensure app modules are importable from tests
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
