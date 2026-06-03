"""
Tests for billing plan gating logic.

Run: cd apps/api && pytest tests/test_billing.py -v
"""
import pytest
from routers.billing import PLANS, _plan_from_stripe, _period_end_from_stripe
from constants import PLAN_FEATURES, TIER_ORDER, is_plan_sufficient


def test_all_plans_have_required_feature_keys():
    required = {"personas", "memory", "rituals", "insights"}
    for plan_name, features in PLAN_FEATURES.items():
        missing = required - set(features.keys())
        assert not missing, f"Plan '{plan_name}' missing keys: {missing}"


def test_free_plan_has_limited_personas():
    assert PLAN_FEATURES["free"]["personas"] == 2


def test_free_plan_no_memory():
    assert PLAN_FEATURES["free"]["memory"] is False


def test_pro_plan_unlimited_personas():
    assert PLAN_FEATURES["pro"]["personas"] == -1


def test_pro_plan_has_memory():
    assert PLAN_FEATURES["pro"]["memory"] is True


def test_premium_has_premium_packs():
    assert PLAN_FEATURES["premium"].get("premium_packs") is True


def test_plan_from_stripe_defaults_to_free():
    """Stripe sub with no recognised price IDs → free."""
    sub_obj = {"items": {"data": [{"price": {"id": "price_unknown"}}]}}
    assert _plan_from_stripe(sub_obj) == "free"


def test_plan_from_stripe_empty_items():
    sub_obj = {"items": {"data": []}}
    assert _plan_from_stripe(sub_obj) == "free"


def test_plans_dict_has_pro_and_premium():
    assert "pro_monthly" in PLANS
    assert "pro_yearly" in PLANS
    assert "premium_monthly" in PLANS


# ── Tier ordering ─────────────────────────────────────────────────────────────

def test_tier_order_free_less_than_pro():
    assert TIER_ORDER["free"] < TIER_ORDER["pro"]
    assert TIER_ORDER["pro"] < TIER_ORDER["premium"]


def test_free_user_cannot_access_pro_ritual():
    assert not is_plan_sufficient("free", "pro")


def test_pro_user_can_access_free_ritual():
    assert is_plan_sufficient("pro", "free")


def test_premium_user_can_access_pro_ritual():
    assert is_plan_sufficient("premium", "pro")


def test_unknown_plan_treated_as_free():
    assert not is_plan_sufficient("enterprise_fake", "pro")


def test_period_end_prefers_items():
    obj = {"items": {"data": [{"current_period_end": 111}]}, "current_period_end": 999}
    assert _period_end_from_stripe(obj) == 111

def test_period_end_falls_back_to_top_level():
    obj = {"items": {"data": [{}]}, "current_period_end": 999}
    assert _period_end_from_stripe(obj) == 999

def test_period_end_none_when_absent():
    obj = {"items": {"data": []}}
    assert _period_end_from_stripe(obj) is None
