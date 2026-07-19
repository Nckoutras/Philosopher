"""Byte-exactness + shape tests for prompt-cache splitting (PR-OPT-1b).

The hard constraint: prompt caching changes billing only — the EXACT same bytes
must reach the model. These tests assert that splitting a sentinel-tagged render
into cache blocks reconstructs the sentinel-free render byte-for-byte, and that
the block shapes are correct.

Run: cd apps/api && pytest tests/services/test_prompt_cache.py -v
"""
import pytest

from services.prompt_builder import PromptBuilder, CACHE_SPLIT_SENTINEL
from personas import get_persona


@pytest.fixture
def builder():
    return PromptBuilder()


class FakeMemory:
    entry_type = "struggle"
    content = "User struggles with procrastination"


class FakePassage:
    source_title = "Meditations"
    source_type = "primary_text"
    page_ref = "Book IV.3"
    content = "Men seek retreats for themselves in the country, by the sea, in the hills."


# ── (a) THE non-negotiable guardrail: same bytes reach the model ──────────────

@pytest.mark.parametrize("slug", ["marcus_aurelius", "socrates"])
def test_split_reconstructs_sentinel_free_render_byte_for_byte(builder, slug):
    persona = get_persona(slug)
    kwargs = dict(persona=persona, memories=[FakeMemory()], passages=[FakePassage()])

    with_sentinel = builder.build_system(include_cache_sentinel=True, **kwargs)
    without_sentinel = builder.build_system(include_cache_sentinel=False, **kwargs)

    # The flag is the only difference: sentinel present vs absent.
    assert CACHE_SPLIT_SENTINEL in with_sentinel
    assert CACHE_SPLIT_SENTINEL not in without_sentinel

    blocks = builder.split_system_for_cache(with_sentinel)
    assert isinstance(blocks, list)
    reconstructed = blocks[0]["text"] + blocks[1]["text"]

    # Prefix + suffix must equal the pre-caching render, byte-for-byte.
    assert reconstructed == without_sentinel


# ── (b) split output shape: exactly 2 blocks, cache_control on block 1 only ────

@pytest.mark.parametrize("slug", ["marcus_aurelius", "socrates"])
def test_split_shape_two_blocks_cache_on_first_only(builder, slug):
    persona = get_persona(slug)
    system = builder.build_system(persona=persona, include_cache_sentinel=True)

    blocks = builder.split_system_for_cache(system)
    assert isinstance(blocks, list) and len(blocks) == 2
    assert blocks[0]["type"] == "text" and blocks[1]["type"] == "text"
    assert blocks[0]["cache_control"] == {"type": "ephemeral"}
    assert "cache_control" not in blocks[1]


# ── Safe no-op fallback: no sentinel → string returned unchanged ──────────────

def test_no_sentinel_passthrough_returns_identical_string(builder):
    persona = get_persona("marcus_aurelius")
    system = builder.build_system(persona=persona)  # default: include_cache_sentinel=False
    result = builder.split_system_for_cache(system)
    assert result is system  # identical object → byte-identical, safe no-op for excluded callers


# ── Council whole-cache: single fully-cached block ────────────────────────────

def test_cache_whole_system_single_cached_block(builder):
    persona = get_persona("marcus_aurelius")
    system = builder.build_system(persona=persona)  # council builds without a sentinel
    blocks = builder.cache_whole_system(system)
    assert len(blocks) == 1
    assert blocks[0]["text"] == system
    assert blocks[0]["cache_control"] == {"type": "ephemeral"}
