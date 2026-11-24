"""
Check that the Gemini API key in backend/.env works.

Run it from the backend folder with the backend's Python environment active:

    python ..\\scripts\\check_gemini.py

It prints which model the assistant will use and sends one tiny request.
The API key itself is never printed.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "backend"))

from app.configuration.config import settings  # noqa: E402
from app.services.llm_service import llm_service  # noqa: E402


def main():
    print(f"LLM_PROVIDER in backend/.env : {settings.LLM_PROVIDER!r}")
    print(f"GEMINI_API_KEY in backend/.env: {'set (' + str(len(settings.GEMINI_API_KEY.strip())) + ' characters)' if settings.GEMINI_API_KEY.strip() else 'NOT SET'}")
    print(f"GEMINI_MODEL                  : {settings.GEMINI_MODEL or '(empty: newest stable Flash model is chosen automatically)'}")
    if not llm_service.has_model:
        print("\nNo language model is configured, so the assistant uses its built-in writer.")
        print("Put LLM_PROVIDER=gemini and GEMINI_API_KEY=... in backend/.env (not in .env.example) and run this again.")
        sys.exit(1)

    models = llm_service.gemini_models()
    if models:
        print(f"Flash models on your account (newest first): {', '.join(models)}")
    print("\nSending a test request...")
    result = llm_service.test_connection()
    print(f"Model used : {result['model']}")
    if result["ok"]:
        print(f"Reply      : {result['reply']!r}")
        print("\nOK - Gemini works. Restart the backend if it is running, so it picks up the settings.")
    else:
        print(f"Problem    : {result.get('last_error')}")
        print("\nTips: a 401/403 means the key is wrong or not enabled for the Gemini API; a 404 means the model")
        print("name does not exist (empty GEMINI_MODEL lets the backend choose); 429 means the free quota is used up;")
        print("503 means Google's servers are busy for every model tried - wait a few minutes and run this again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
