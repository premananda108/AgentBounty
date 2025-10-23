"""Auth0 authentication routes"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from app.config import settings


router = APIRouter(prefix="/auth", tags=["auth"])

# OAuth client configuration
oauth = OAuth()
oauth.register(
    name='auth0',
    client_id=settings.AUTH0_CLIENT_ID,
    client_secret=settings.AUTH0_CLIENT_SECRET,
    server_metadata_url=f'https://{settings.AUTH0_DOMAIN}/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid profile email offline_access'
    }
)


@router.get("/login")
async def login(request: Request):
    """
    Initiate Auth0 login flow

    User will be redirected to Auth0 login page.
    After successful login, Auth0 redirects back to /auth/callback
    """
    # Clear session before login to prevent state mismatch
    request.session.clear()

    redirect_uri = settings.AUTH0_CALLBACK_URL
    return await oauth.auth0.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def callback(request: Request):
    """
    Handle Auth0 callback

    Auth0 redirects here after successful authentication.
    We extract user info and create session.
    """
    try:
        # Get token from Auth0
        token = await oauth.auth0.authorize_access_token(request)

        # Extract user info
        user_info = dict(token['userinfo'])

        # Debug: Log what we received
        print(f"🔍 DEBUG: Token keys: {token.keys()}")
        print(f"🔍 DEBUG: User info: {user_info}")
        print(f"🔍 DEBUG: User sub: {user_info.get('sub')}")
        print(f"🔍 DEBUG: User email: {user_info.get('email')}")
        print(f"🔍 DEBUG: User nickname: {user_info.get('nickname')}")
        print(f"🔍 DEBUG: User name: {user_info.get('name')}")

        # Store in session
        request.session['user'] = user_info
        request.session['auth0_access_token'] = token.get('access_token')

        # Auth0 Token Vault automatically stored Google/GitHub tokens
        # Agents will retrieve them via Management API when needed

        email_or_nickname = user_info.get('email') or user_info.get('nickname') or user_info.get('name') or 'Unknown'
        print(f"✅ User logged in: {email_or_nickname}")

        # Redirect to frontend
        return RedirectResponse(url="/")

    except Exception as e:
        print(f"❌ Auth callback error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")


@router.get("/logout")
async def logout(request: Request):
    """
    Logout user

    Clears session and redirects to Auth0 logout
    """
    # Clear session
    request.session.clear()

    # Redirect to Auth0 logout
    logout_url = (
        f'https://{settings.AUTH0_DOMAIN}/v2/logout?'
        f'client_id={settings.AUTH0_CLIENT_ID}&'
        f'returnTo=http://localhost:{settings.PORT}'
    )

    return RedirectResponse(url=logout_url)


@router.get("/user")
async def get_current_user(request: Request):
    """
    Get current authenticated user

    Returns user info from session
    """
    user = request.session.get('user')

    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return {
        "user": user,
        "authenticated": True
    }


def require_auth(request: Request) -> dict:
    """
    Dependency to require authentication

    Usage:
        @router.get("/protected")
        async def protected(request: Request, user=Depends(require_auth)):
            return {"user": user}
    """
    user = request.session.get('user')

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user


async def require_mcp_auth(request: Request) -> dict:


    """


    Dependency for MCP service-to-service authentication.


    Now validates that the user from X-User-ID exists in Auth0.


    """


    from app.services.auth0_service import Auth0Service





    # Check for service token in Authorization header


    auth_header = request.headers.get('Authorization')





    if auth_header and auth_header.startswith('Bearer '):


        token = auth_header.replace('Bearer ', '')





        if not settings.MCP_SERVICE_TOKEN:


            raise ValueError("MCP_SERVICE_TOKEN is not configured on the main application server.")





        if token == settings.MCP_SERVICE_TOKEN:


            user_id = request.headers.get('X-User-ID')


            if not user_id:


                raise HTTPException(status_code=400, detail="X-User-ID header required for MCP authentication")





            # Verify user exists in Auth0


            auth0_service = Auth0Service()


            user_profile = await auth0_service.get_user_profile(user_id)


            if not user_profile:


                raise HTTPException(status_code=404, detail=f"User with ID '{user_id}' not found in Auth0.")





            # Return a structure compatible with Auth0 user info, plus our flag


            user_profile['mcp_service'] = True


            return user_profile





    # Fall back to regular session-based auth


    user = request.session.get('user')


    if not user:


        raise HTTPException(


            status_code=401,


            detail="Authentication required (session or MCP service token)",


            headers={"WWW-Authenticate": "Bearer"}


        )





    return user
