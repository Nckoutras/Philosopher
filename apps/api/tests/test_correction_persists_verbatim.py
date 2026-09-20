"""What the reader saw is what the row holds (UAT2-001, Ruling D).

WHY THIS FILE EXISTS. On 2026-09-20 a persona wrote "That's the hinge." The
universal lexicon matched `Hinge` — the dating app — by case-folded substring,
so the reply was regenerated; the correction said "hinge" again; and
_deterministic_strip deleted the word and persisted "That's the .". The client
had ALREADY committed the correction text it streamed (useStream.tsx:162) and
was never told the server had edited it, so the screen and the row disagreed
permanently. There is no canonical source for the lost word: the row is
unrepairable.

RULING D: the server persists the correction text UNMODIFIED, byte-identical to
what the client committed. A forbidden phrase reaching the reader and the row is
the accepted cost — signed off, and measured at 1 in 828 before the fix.

WHY THE STRIP FUNCTION IS STILL HERE AND STILL PASSING ITS 112 TESTS. Ruling D
was implemented by dropping the CALL, not by gutting _deterministic_strip. The
function does three things — span deletion, a whitespace collapse, and a brevity
trim — and removing only the first would have left the other two mutating the
text, which is not byte-identical. So the test below asserts on what
stream_response PERSISTS, not on what the strip function does.

THE MOCKS HERE ARE KEYED ON WHAT THE STATEMENT ASKS FOR, NEVER ON CALL ORDER.
CLAUDE.md's TD-45 entry records 17 tests in one file broken by hard-coded
`execute()` indices; a test written that way is one inserted query away from
asserting nothing. `_FakeSession.execute` reads the compiled SQL to decide what
to hand back, so adding a query upstream cannot silently shift this test's
answers. Per C-06 the conversation, persona and safety objects are plain classes
with every field the code under test reads — a MagicMock would have absorbed
`deep_mode` into a truthy Mock and routed us through the deep-mode limiter.
"""
import uuid

import pytest

from services import conversation_service as cs


# ── Doubles: real objects, every field the code reads (C-06) ──────────────────

class _Conv:
    def __init__(self, cid, pid):
        self.id = cid
        self.persona_id = pid
        self.active_persona_id = None
        self.deep_mode = False
        self.message_count = 2
        self.title = "A title that already exists"
        self.ritual_id = None


class _PersonaRow:
    def __init__(self, slug):
        self.slug = slug


class _Safety:
    """safety_service result. Both check_input and check_output read from this."""
    should_log = False
    should_suppress_persona = False
    level = "none"
    category = None


class _Prefs:
    profile = None


class _FakeResult:
    def __init__(self, one=None, many=None):
        self._one = one
        self._many = many or []

    def scalar_one_or_none(self):
        return self._one

    def scalar_one(self):
        if self._one is None:
            raise AssertionError("scalar_one() on an empty fake result")
        return self._one

    def scalars(self):
        return self

    def all(self):
        return self._many

    def first(self):
        return self._one


class _FakeSession:
    """Answers by WHAT IS ASKED FOR, not by call index. See the module docstring."""

    def __init__(self, conv, persona_row):
        self._conv = conv
        self._persona_row = persona_row

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def execute(self, stmt, *a, **kw):
        sql = str(stmt).lower()
        if "from conversations" in sql:
            return _FakeResult(one=self._conv)
        if "from personas" in sql:
            return _FakeResult(one=self._persona_row)
        # messages history, daily_usage, name lookups, UPDATEs: empty is correct
        # for a turn that needs no history and has no usage row yet.
        return _FakeResult(one=None, many=[])

    async def commit(self):
        return None

    async def rollback(self):
        return None

    async def flush(self):
        return None

    def add(self, obj):
        return None


class _SavedMessage:
    """Stands in for models.Message.

    `id` is a STRING, not a uuid.UUID — models.Message.id is
    `UUID(as_uuid=False)`, so SQLAlchemy hands back `str`, and the `done` event
    puts it straight through json.dumps with no coercion
    (conversation_service.py:1268). A uuid.UUID here raises TypeError inside the
    generator and the test fails somewhere unrelated to what it asserts. CLAUDE.md
    TD-76: every field, with the right TYPE, checked against the model.
    """

    def __init__(self, content):
        self.id = str(uuid.uuid4())
        self.content = content
        self.created_at = None


@pytest.fixture
def correction_harness(monkeypatch):
    """Drive stream_response through the correction branch and capture the row.

    Returns a callable: run(first_reply, correction_reply) -> persisted assistant
    text. The first reply trips the lexicon, which forces the correction; what
    the correction returns is the subject of every assertion below.
    """
    conv_id = str(uuid.uuid4())
    persona_id = uuid.uuid4()
    conv = _Conv(conv_id, persona_id)
    persona_row = _PersonaRow("marcus_aurelius")

    def _factory():
        return _FakeSession(conv, persona_row)

    monkeypatch.setattr(cs, "safety_service", _StubSafety())
    monkeypatch.setattr(cs, "embedding_client", _StubEmbed())
    monkeypatch.setattr(cs, "memory_service", _StubMemory())
    monkeypatch.setattr(cs, "retrieval_service", _StubRetrieval())
    monkeypatch.setattr(cs, "phenomenology_bridge_service", _StubBridge())
    monkeypatch.setattr(cs, "analytics_service", _StubAnalytics())
    monkeypatch.setattr(cs, "get_user_preferences", _stub_prefs)
    monkeypatch.setattr(cs.prompt_builder, "build_system", lambda *a, **kw: "SYSTEM")
    monkeypatch.setattr(
        cs.prompt_builder, "split_system_for_cache", lambda s: [{"text": s}]
    )

    async def run(first_reply: str, correction_reply: str) -> str:
        replies = [first_reply, correction_reply]
        captured: list[str] = []

        async def _fake_stream(*a, **kw):
            text = replies.pop(0)
            for i in range(0, len(text), 16):
                yield text[i:i + 16]

        async def _fake_save(self, db, conv_, user_id, role, content, **kw):
            if role == "assistant":
                captured.append(content)
            return _SavedMessage(content)

        monkeypatch.setattr(cs.llm_client, "stream", _fake_stream)
        monkeypatch.setattr(cs.ConversationService, "_save_message", _fake_save)

        svc = cs.ConversationService()
        async for _ in svc.stream_response(
            session_factory=_factory,
            conversation_id=conv_id,
            user_id=str(uuid.uuid4()),
            user_text="I keep choosing stability over meaningful work.",
        ):
            pass

        assert not replies, "the correction branch never fired — the first reply did not trip"
        assert captured, "no assistant message was persisted"
        return captured[-1]

    return run


class _StubSafety:
    async def check_input(self, *a, **kw):
        return _Safety()

    async def check_output(self, *a, **kw):
        return _Safety()


class _StubEmbed:
    async def embed(self, *a, **kw):
        return [0.0] * 8


class _StubMemory:
    async def recall(self, *a, **kw):
        return []


class _StubRetrieval:
    async def retrieve(self, *a, **kw):
        return []


class _StubBridge:
    def lookup(self, *a, **kw):
        return None


class _StubAnalytics:
    def track(self, *a, **kw):
        return None


async def _stub_prefs(*a, **kw):
    return _Prefs()


# A phrase still in the lexicon after Ruling C, used to force the correction
# branch. `Instagram` is a brand with no English meaning — exactly the kind of
# entry the lexicon is FOR, which is why it survived curation.
TRIPS = "She tells me it is all over Instagram now."


@pytest.mark.asyncio
async def test_a_failed_correction_persists_the_correction_text_unmodified(correction_harness):
    """The whole of Ruling D, in one assertion.

    Both replies trip the lexicon, so the correction fails its re-check and lands
    in the branch that used to strip. What is persisted must be the correction,
    character for character.
    """
    correction = "Instagram is not the point, and you know it."
    persisted = await correction_harness(TRIPS, correction)
    assert persisted == correction


@pytest.mark.asyncio
async def test_whitespace_in_a_failed_correction_survives_verbatim(correction_harness):
    """Byte-identical means the whitespace too.

    _deterministic_strip collapsed runs of whitespace and .strip()ped the ends
    REGARDLESS of whether anything was removed, so a correction that merely
    failed the check came back reshaped even when no span matched. This is the
    assertion that fails if the call is ever restored for "just" the tidy-up.
    """
    correction = "  Instagram.  Two  spaces  inside, and padding outside.  "
    persisted = await correction_harness(TRIPS, correction)
    assert persisted == correction


@pytest.mark.asyncio
async def test_the_forbidden_phrase_reaches_the_row(correction_harness):
    """The accepted consequence, pinned so it cannot be quietly re-closed.

    Ruling D trades a rare surviving brand name for never editing text behind the
    reader. If someone reinstates stripping, this fails — and it should, because
    the trade is a founder ruling and not an oversight.
    """
    correction = "Instagram, again, and I will not pretend otherwise."
    persisted = await correction_harness(TRIPS, correction)
    assert "Instagram" in persisted


def test_conversation_service_cannot_reach_the_strip():
    """The structural half: the call is gone, so the import is gone.

    Behaviour above proves what is persisted today. This proves there is no
    transform left in the module to reach — restoring one means restoring this
    import, which makes the change visible in review rather than buried in a
    branch nobody reads.
    """
    assert not hasattr(cs, "_deterministic_strip"), (
        "_deterministic_strip is importable in conversation_service again — "
        "UAT2-001 Ruling D says the correction text is persisted unmodified"
    )
