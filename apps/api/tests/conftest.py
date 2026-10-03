import sys
import os

# Set dummy credentials before any service module is imported.
# Services that wrap external clients (OpenAI, Anthropic) instantiate those
# clients at module load time; a missing/empty key raises immediately.
os.environ.setdefault('OPENAI_API_KEY', 'sk-test-dummy')
os.environ.setdefault('ANTHROPIC_API_KEY', 'test-dummy')

# SAFETY-002: no test may reach the judge's network call. With the kill switch off,
# every Tier-B message behaves as a judge FAILURE — fail-closed, the lexicon level
# stands — which is exactly the pre-judge behaviour, so existing tests keep their
# meaning. The judge's own tests switch it on with a mocked client.
os.environ.setdefault('SAFETY_JUDGE_ENABLED', 'false')

# MEM2-B5: the same rule for the dedup judge. OFF is exactly the pre-B5 write
# path, so every existing memory test keeps its meaning — several of them give
# every row one shared fake embedding, which B5 would read as duplicates. The
# B5 tests switch it on and stub the judge.
os.environ.setdefault('MEMORY_DEDUP_ENABLED', 'false')

# Ensure app modules are importable from tests
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
