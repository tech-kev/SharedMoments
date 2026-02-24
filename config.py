import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY environment variable must be set. Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\"")
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'app/database/sharedmomentsv2.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # WebAuthn
    WEBAUTHN_RP_ID = os.environ.get('WEBAUTHN_RP_ID') or 'localhost'
    WEBAUTHN_RP_NAME = os.environ.get('WEBAUTHN_RP_NAME') or 'SharedMoments'
    WEBAUTHN_ORIGIN = os.environ.get('WEBAUTHN_ORIGIN') or 'http://localhost:5001'

    # AI Provider
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    ANTHROPIC_MODEL = os.environ.get('ANTHROPIC_MODEL', 'claude-haiku-4-5')
    OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL')
    OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3.2')
    AI_SYSTEM_PROMPT = os.environ.get('AI_SYSTEM_PROMPT')
