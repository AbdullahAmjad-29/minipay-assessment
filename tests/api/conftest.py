"""Shared fixtures for the API test suite. BASE_URL and API_KEY are read
from the environment so this suite can point at local, Docker, or the
Kubernetes-deployed instance without code changes.
"""
import os
import pytest

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
API_KEY = os.getenv("API_KEY", "dev-secret-key-change-in-production")


@pytest.fixture
def base_url():
    return BASE_URL


@pytest.fixture
def auth_headers():
    return {"X-API-Key": API_KEY, "Content-Type": "application/json"}


@pytest.fixture
def no_auth_headers():
    return {"Content-Type": "application/json"}
