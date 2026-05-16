import sys
import os

os.environ.setdefault('OPENAI_API_KEY', 'sk-test-dummy')
os.environ.setdefault('ANTHROPIC_API_KEY', 'test-dummy')

# Add apps/api/ to sys.path so models and db packages are importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
