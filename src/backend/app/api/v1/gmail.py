import logging
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_session
from app.schemas.inbox import AuthorizationUrl, InboxDraft
from app.services import gmail_oauth
from app.services.gmail_oauth import OAuthError
from app.services.inboxes import save_gmail_inbox

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/email/gmail", tags=["gmail"])

# Frontend page the OAuth callback returns to.
FRONTEND_RETURN_PATH = "/connections/inbox"


def _frontend_redirect(**params: str) -> RedirectResponse:
    url = f"{get_settings().frontend_url}{FRONTEND_RETURN_PATH}?{urlencode(params)}"
    return RedirectResponse(url, status_code=303)


@router.post("/authorize", response_model=AuthorizationUrl)
async def authorize(draft: InboxDraft):
    """Start connecting a Gmail inbox. The client navigates the browser to the returned URL."""
    return AuthorizationUrl(authorization_url=await gmail_oauth.start_authorization(draft))


@router.get("/callback", include_in_schema=False)
async def callback(
    session: Annotated[AsyncSession, Depends(get_session)],
    state: str | None = None,
    code: str | None = None,
    error: str | None = None,
):
    """Google redirects here after consent. Always ends with a redirect back to the frontend."""
    try:
        if state is None:
            raise OAuthError("invalid_state")
        pending = await gmail_oauth.consume_state(state)
        if error is not None:
            raise OAuthError("access_denied" if error == "access_denied" else "google_error", error)
        if code is None:
            raise OAuthError("missing_code")

        tokens = await gmail_oauth.exchange_code(code, pending.code_verifier)
        email_address = await gmail_oauth.fetch_email_address(tokens.access_token)
        inbox, created = await save_gmail_inbox(session, pending.draft, email_address, tokens)
    except OAuthError as exc:
        logger.warning("Gmail OAuth failed: %s (%s)", exc.code, exc)
        return _frontend_redirect(oauth="error", reason=exc.code)

    return _frontend_redirect(oauth="connected" if created else "reconnected", inbox=str(inbox.id))
