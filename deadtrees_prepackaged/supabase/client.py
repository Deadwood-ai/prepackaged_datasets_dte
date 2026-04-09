from __future__ import annotations

from supabase import Client, ClientOptions, create_client


def create_supabase_client(url: str, key: str) -> Client:
	return create_client(url, key, options=ClientOptions(auto_refresh_token=False))
