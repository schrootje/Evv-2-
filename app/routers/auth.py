from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from app.auth.oauth import exchange_code, get_authorization_url

router = APIRouter(prefix="/auth", tags=["Authenticatie"])


@router.get("/login", summary="Start OAuth2 login flow")
def login():
    """Redirect naar Exact Online voor autorisatie."""
    return RedirectResponse(url=get_authorization_url())


@router.get("/callback", summary="OAuth2 callback")
def callback(code: str):
    """Exact Online stuurt de gebruiker hier naartoe met een autorisatiecode."""
    tokens = exchange_code(code)
    return {
        "message": "Authenticatie geslaagd. Tokens opgeslagen.",
        "expires_in": tokens.get("expires_in"),
    }
