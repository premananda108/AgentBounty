"""Auth0 Management API Service"""
import httpx
from typing import Dict, Optional
from datetime import datetime, timedelta
from app.config import settings


class Auth0Service:
    """Service for Auth0 Management API interactions"""

    def __init__(self):
        self.domain = settings.AUTH0_DOMAIN
        self.m2m_client_id = settings.AUTH0_M2M_CLIENT_ID
        self.m2m_client_secret = settings.AUTH0_M2M_CLIENT_SECRET
        self.audience = settings.AUTH0_AUDIENCE
        self._management_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

        # Cache for user profiles (user_id -> (profile, expires_at))
        self._user_profile_cache: Dict[str, tuple] = {}

    async def get_management_token(self) -> str:
        """Get M2M token for Auth0 Management API (with caching)"""
        # Check if we have a valid cached token
        if self._management_token and self._token_expires_at:
            if datetime.utcnow() < self._token_expires_at:
                return self._management_token

        # Get new token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f'https://{self.domain}/oauth/token',
                json={
                    'client_id': self.m2m_client_id,
                    'client_secret': self.m2m_client_secret,
                    'audience': self.audience,
                    'grant_type': 'client_credentials'
                },
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()

            # Cache token for 23 hours (expires in 24h)
            self._management_token = data['access_token']
            self._token_expires_at = datetime.utcnow() + timedelta(hours=23)

            return self._management_token

    async def get_user_profile(self, user_id: str, force_refresh: bool = False) -> Optional[Dict]:
        """
        Get full user profile from Auth0 (with caching)

        Args:
            user_id: Auth0 user ID
            force_refresh: Skip cache and fetch fresh data

        Returns:
            User profile dict or None
        """
        # Check cache first (unless force refresh)
        if not force_refresh and user_id in self._user_profile_cache:
            cached_profile, expires_at = self._user_profile_cache[user_id]
            if datetime.utcnow() < expires_at:
                print(f"📦 Using cached profile for {user_id}")
                return cached_profile

        # Fetch from Auth0
        try:
            token = await self.get_management_token()

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f'https://{self.domain}/api/v2/users/{user_id}',
                    headers={'Authorization': f'Bearer {token}'},
                    timeout=10.0
                )
                response.raise_for_status()
                profile = response.json()

                # Cache for 5 minutes
                self._user_profile_cache[user_id] = (
                    profile,
                    datetime.utcnow() + timedelta(minutes=5)
                )

                print(f"✅ Fetched and cached profile for {user_id}")
                return profile

        except Exception as e:
            print(f"❌ Error getting user profile: {e}")

            # If we have stale cache, return it as fallback
            if user_id in self._user_profile_cache:
                print(f"⚠️  Returning stale cached profile for {user_id}")
                cached_profile, _ = self._user_profile_cache[user_id]
                return cached_profile

            return None

    async def update_user_metadata(self, user_id: str, metadata: dict):
        """
        Update user metadata in Auth0

        Args:
            user_id: Auth0 user ID (sub claim)
            metadata: Dictionary to merge with existing user_metadata
        """
        try:
            token = await self.get_management_token()

            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f'https://{self.domain}/api/v2/users/{user_id}',
                    headers={
                        'Authorization': f'Bearer {token}',
                        'Content-Type': 'application/json'
                    },
                    json={'user_metadata': metadata},
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()

        except Exception as e:
            print(f"❌ Error updating user metadata: {e}")
            return None

    async def get_user_wallet(self, user_id: str) -> Optional[str]:
        """
        Get wallet address from user metadata

        Args:
            user_id: Auth0 user ID

        Returns:
            Wallet address or None if not connected
        """
        profile = await self.get_user_profile(user_id)
        if not profile:
            return None

        user_metadata = profile.get('user_metadata', {})
        return user_metadata.get('wallet_address')


# Global service instance
auth0_service = Auth0Service()
