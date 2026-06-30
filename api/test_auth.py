"""
WardWatch API - Auth Middleware Test Script
Usage:
  1. Obtain a Firebase ID token from the mobile app or Firebase Auth REST API
  2. Set the TOKEN environment variable
  3. Run: python test_auth.py

NOTE: Do NOT hardcode any tokens in this file.
This test script is for local development only.
"""
import os
import asyncio
import httpx

# Test configuration - set via environment variable, never hardcode
TEST_TOKEN = os.environ.get("WARDWATCH_TEST_TOKEN", "")
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8080")


async def test_health_endpoint():
    """Test the /health endpoint (no auth required)."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/health")
    assert response.status_code == 200, f"Health check failed: {response.text}"
    data = response.json()
    assert data["status"] == "healthy", f"Unexpected status: {data}"
    print(f"[PASS] Health endpoint: {data}")


async def test_auth_missing_token():
    """Test that missing token returns 401."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/api/v1/issues/nearby",
            params={"lat": 19.0760, "lng": 72.8777},
        )
    assert response.status_code == 401, (
        f"Expected 401 for missing token, got {response.status_code}: {response.text}"
    )
    print(f"[PASS] Missing token returns 401.")


async def test_auth_invalid_token():
    """Test that an invalid token returns 401."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/api/v1/issues/nearby",
            params={"lat": 19.0760, "lng": 72.8777},
            headers={"Authorization": "Bearer invalid.token.here"},
        )
    assert response.status_code == 401, (
        f"Expected 401 for invalid token, got {response.status_code}: {response.text}"
    )
    print(f"[PASS] Invalid token returns 401.")


async def test_auth_valid_token():
    """Test that a valid token is accepted. Requires WARDWATCH_TEST_TOKEN env var."""
    if not TEST_TOKEN:
        print("[SKIP] test_auth_valid_token: WARDWATCH_TEST_TOKEN not set.")
        return
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/api/v1/issues/nearby",
            params={"lat": 19.0760, "lng": 72.8777},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
    # 200 or 422 (if required params are wrong) but NOT 401/403
    assert response.status_code not in (401, 403), (
        f"Valid token was rejected: {response.status_code}: {response.text}"
    )
    print(f"[PASS] Valid token accepted (status: {response.status_code}).")


async def main():
    print("=== WardWatch Auth Middleware Tests ===")
    print(f"API Base URL: {API_BASE_URL}")
    print("")
    await test_health_endpoint()
    await test_auth_missing_token()
    await test_auth_invalid_token()
    await test_auth_valid_token()
    print("")
    print("=== All tests passed ===")


if __name__ == "__main__":
    asyncio.run(main())
