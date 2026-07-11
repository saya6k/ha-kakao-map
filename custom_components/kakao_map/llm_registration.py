"""Thin llm.API shell for kakao_map, registered once at component setup.

Deliberately kept outside the `llm/` platform package and does not import
`homeassistant.components.llm` at module scope: doing either would force our
tool modules (and HA's own new `llm` integration, absent on HA < 2026.8) to
import at kakao_map setup time instead of on the first LLM request, defeating
HA's lazy platform loading (see `llm/__init__.py`) and breaking setup outright
on older HA. The one call that needs `homeassistant.components.llm` is
deferred into `async_get_api_instance`, which only ever runs once that
integration exists and has requested an instance.

On HA < 2026.8, `homeassistant.components.llm` doesn't exist at all yet — not
merely unset up — so `KakaoMapAPI` still registers fine (registration never
touches it), but if a user has selected "Kakao Map" as their conversation
agent's LLM API and the agent then calls `async_get_api_instance`, that
import would raise ModuleNotFoundError. Caught below and degraded to an
empty-tools instance instead of crashing the conversation turn.
"""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm
from homeassistant.helpers.issue_registry import (
    IssueSeverity,
    async_create_issue,
    async_delete_issue,
)

from .const import API_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

ISSUE_LLM_TOOLS_UNAVAILABLE = "llm_tools_require_2026_8"


class KakaoMapAPI(llm.API):
    """Exposes kakao_map's tools by aggregating the `llm` platform hooks."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize with kakao_map's stable API id."""
        super().__init__(hass=hass, id=DOMAIN, name=API_NAME)

    async def async_get_api_instance(self, llm_context: llm.LLMContext) -> llm.APIInstance:
        """Return the instance of the API."""
        try:
            from homeassistant.components.llm import (  # noqa: PLC0415
                async_get_tools as async_get_platform_tools,
            )
        except ModuleNotFoundError:
            _LOGGER.warning(
                "Kakao Map tools require Home Assistant 2026.8 or later; "
                "none are available on this version"
            )
            async_create_issue(
                self.hass,
                DOMAIN,
                ISSUE_LLM_TOOLS_UNAVAILABLE,
                is_fixable=False,
                severity=IssueSeverity.WARNING,
                translation_key=ISSUE_LLM_TOOLS_UNAVAILABLE,
                learn_more_url="https://github.com/saya6k/hacs-kakao-map",
            )
            return llm.APIInstance(
                api=self, api_prompt="", llm_context=llm_context, tools=[]
            )

        async_delete_issue(self.hass, DOMAIN, ISSUE_LLM_TOOLS_UNAVAILABLE)
        llm_tools = await async_get_platform_tools(self.hass, llm_context, self.id)
        return llm.APIInstance(
            api=self,
            api_prompt=llm_tools.prompt or "",
            llm_context=llm_context,
            tools=llm_tools.tools,
        )
