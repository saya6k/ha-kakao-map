"""KakaoMapAPI's behavior on HA < 2026.8, where homeassistant.components.llm doesn't exist.

Mirror image of tests/test_llm_api.py's pytest.importorskip guard: this only runs
when homeassistant.components.llm is NOT importable. Run scripts/test (stable
track) to exercise it for real; it's a no-op skip under scripts/test-dev.
"""

from __future__ import annotations

import importlib.util

import pytest
from homeassistant.const import CONF_API_KEY
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers import llm

from custom_components.kakao_map.const import DOMAIN
from custom_components.kakao_map.llm_registration import ISSUE_LLM_TOOLS_UNAVAILABLE
from tests.vendor.ha_common import MockConfigEntry

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("homeassistant.components.llm") is not None,
    reason="only exercises the pre-2026.8 fallback when homeassistant.components.llm is absent",
)


async def test_async_get_api_instance_degrades_gracefully_without_llm_integration(
    hass: HomeAssistant,
) -> None:
    """Selecting Kakao Map as the LLM API on HA < 2026.8 returns no tools, not a crash."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_API_KEY: "test-key"}, unique_id=DOMAIN)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    api = next(a for a in llm.async_get_apis(hass) if a.id == DOMAIN)
    instance = await api.async_get_api_instance(
        llm.LLMContext(
            platform="test", context=Context(), language="ko", assistant="test", device_id=None
        )
    )

    assert instance.tools == []

    issue = ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_LLM_TOOLS_UNAVAILABLE)
    assert issue is not None
    assert issue.severity == ir.IssueSeverity.WARNING
