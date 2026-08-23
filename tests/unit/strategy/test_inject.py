"""Injection seam tests: resolve_brain_cls and resolve_brain.

TC-P17: explicit police_class selector loads custom class end-to-end;
        malformed selector => ValueError; missing attribute => ValueError;
        non-BrainBase target => TypeError; unset selector => shipped PoliceBrain.
"""

from __future__ import annotations

import random
import sys

import pytest

from common.domain.scoring import Role
from police_peer.strategy import resolve_brain, resolve_brain_cls
from police_peer.strategy.base import BrainBase
from police_peer.strategy.hint_types import ProviderReply, TokenUsage
from police_peer.strategy.police import PoliceBrain


class _FakeProvider:
    """Minimal TextProvider stand-in (structural, no live call)."""

    def render(self, request, *, deadline=None):
        return ProviderReply(text="ok", usage=TokenUsage(0, 0), provider="fake", model="fake")


class _FakeModule:
    """A fake module for testing import resolution."""

    def __init__(self) -> None:
        self.__name__ = "test_fake_module"


class TestResolveBrainCls:
    """TC-P17: injection seam fail-fast behavior."""

    def test_unset_selector_returns_police_brain(self) -> None:
        cls = resolve_brain_cls(None, Role.POLICE)
        assert cls is PoliceBrain

    def test_empty_config_returns_police_brain(self) -> None:
        cls = resolve_brain_cls({}, Role.POLICE)
        assert cls is PoliceBrain

    def test_malformed_selector_value_error(self) -> None:
        config = {"strategy": {"police_class": "no_colon"}}
        with pytest.raises(ValueError, match="malformed"):
            resolve_brain_cls(config, Role.POLICE)

    def test_missing_module_value_error(self) -> None:
        config = {"strategy": {"police_class": "nonexistent_module:SomeClass"}}
        with pytest.raises(ValueError, match="not found"):
            resolve_brain_cls(config, Role.POLICE)

    def test_missing_class_value_error(self) -> None:
        config = {"strategy": {"police_class": "os:NonExistentClass"}}
        with pytest.raises(ValueError, match="not found"):
            resolve_brain_cls(config, Role.POLICE)

    def test_non_brainbase_type_error(self) -> None:
        config = {"strategy": {"police_class": "os:path"}}
        with pytest.raises(TypeError, match="not a BrainBase subclass"):
            resolve_brain_cls(config, Role.POLICE)

    def test_custom_class_loaded(self) -> None:
        """Register a fake module with a BrainBase subclass."""
        fake = _FakeModule()

        class CustomBrain(BrainBase):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def _decide_move(self, state, belief):
                return "MOVE:N", None

        fake.CustomBrain = CustomBrain
        sys.modules["test_fake_module"] = fake

        try:
            config = {"strategy": {"police_class": "test_fake_module:CustomBrain"}}
            cls = resolve_brain_cls(config, Role.POLICE)
            assert cls is CustomBrain
            assert issubclass(cls, BrainBase)
        finally:
            del sys.modules["test_fake_module"]

    def test_thief_selector_ignored_for_police(self) -> None:
        config = {"strategy": {"thief_class": "os:path"}}
        cls = resolve_brain_cls(config, Role.POLICE)
        assert cls is PoliceBrain


class TestResolveBrain:
    """TC-P17 end-to-end: resolve_brain instantiates with correct params."""

    def test_default_police_brain(self) -> None:
        config = {"seed": 42, "world": {"map_area": "New York", "hint_max_words": 15}}
        brain = resolve_brain(config, Role.POLICE)
        assert isinstance(brain, PoliceBrain)
        assert brain.arena == "New York"
        assert brain.max_words == 15

    def test_custom_weights(self) -> None:
        config = {
            "seed": 42,
            "world": {"map_area": "New York", "hint_max_words": 10},
            "strategy": {
                "police": {
                    "min_confidence": 0.25,
                    "barrier_mass_floor": 0.10,
                    "w_mass": 2.0,
                    "w_cut": 0.75,
                    "route_slack": 2,
                    "barrier_reserve": 5,
                    "strong_threshold": 0.9,
                    "barrier_score_threshold": 0.5,
                }
            },
        }
        brain = resolve_brain(config, Role.POLICE)
        assert isinstance(brain, PoliceBrain)
        assert brain.min_confidence == 0.25
        assert brain.barrier_mass_floor == 0.10
        assert brain.w_mass == 2.0
        assert brain.w_cut == 0.75
        assert brain.route_slack == 2
        assert brain.barrier_reserve == 5
        assert brain.strong_threshold == 0.9
        assert brain.barrier_score_threshold == 0.5

    def test_custom_seed(self) -> None:
        config = {"seed": 99, "world": {"map_area": "New York", "hint_max_words": 15}}
        rng = random.Random(99)
        brain = resolve_brain(config, Role.POLICE, rng=rng)
        assert isinstance(brain, PoliceBrain)

    def test_no_config_uses_defaults(self) -> None:
        brain = resolve_brain(None, Role.POLICE)
        assert isinstance(brain, PoliceBrain)
        assert brain.min_confidence == 0.10
        assert brain.barrier_score_threshold == 0.3

    def test_thief_raises(self) -> None:
        """police_repo has no default THIEF brain (SD-P7)."""
        with pytest.raises(ValueError, match="no default brain class"):
            resolve_brain(None, Role.THIEF)


class TestResolveBrainLLM:
    """F-14: the declared `llm` seam must be used, or rejected fail-fast --
    never silently ignored.
    """

    _config = {"seed": 42, "world": {"map_area": "New York", "hint_max_words": 15}}

    def test_llm_is_passed_into_hint_writer(self) -> None:
        provider = _FakeProvider()
        brain = resolve_brain(self._config, Role.POLICE, llm=provider)
        assert brain.hint_writer.provider is provider

    def test_no_llm_defaults_to_none(self) -> None:
        brain = resolve_brain(self._config, Role.POLICE)
        assert brain.hint_writer.provider is None

    def test_non_provider_llm_rejected_fail_fast(self) -> None:
        with pytest.raises(TypeError, match="TextProvider"):
            resolve_brain(self._config, Role.POLICE, llm=object())
