"""Tests für app/ai.py — Provider-Auswahl und System-Prompt."""
import os


def test_provider_openai(monkeypatch):
    """OPENAI_API_KEY gesetzt → openai wird gewählt."""
    monkeypatch.setenv('OPENAI_API_KEY', 'sk-test')
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    monkeypatch.delenv('OLLAMA_BASE_URL', raising=False)

    from app.ai import get_active_provider
    assert get_active_provider() == 'openai'


def test_provider_anthropic(monkeypatch):
    """Nur ANTHROPIC_API_KEY → anthropic wird gewählt."""
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'sk-ant-test')
    monkeypatch.delenv('OLLAMA_BASE_URL', raising=False)

    from app.ai import get_active_provider
    assert get_active_provider() == 'anthropic'


def test_provider_ollama(monkeypatch):
    """Nur OLLAMA_BASE_URL → ollama wird gewählt."""
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    monkeypatch.setenv('OLLAMA_BASE_URL', 'http://localhost:11434')

    from app.ai import get_active_provider
    assert get_active_provider() == 'ollama'


def test_provider_priority(monkeypatch):
    """Mehrere Keys gesetzt → OpenAI hat Priorität."""
    monkeypatch.setenv('OPENAI_API_KEY', 'sk-test')
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'sk-ant-test')
    monkeypatch.setenv('OLLAMA_BASE_URL', 'http://localhost:11434')

    from app.ai import get_active_provider
    assert get_active_provider() == 'openai'


def test_provider_none(monkeypatch):
    """Kein Key gesetzt → None."""
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    monkeypatch.delenv('OLLAMA_BASE_URL', raising=False)

    from app.ai import get_active_provider
    assert get_active_provider() is None


def test_system_prompt_default(monkeypatch):
    """Ohne AI_SYSTEM_PROMPT Env-Var → Default-Prompt."""
    monkeypatch.delenv('AI_SYSTEM_PROMPT', raising=False)

    from app.ai import get_system_prompt, DEFAULT_SYSTEM_PROMPT
    assert get_system_prompt() == DEFAULT_SYSTEM_PROMPT


def test_system_prompt_custom(monkeypatch):
    """AI_SYSTEM_PROMPT gesetzt → Custom-Prompt."""
    monkeypatch.setenv('AI_SYSTEM_PROMPT', 'Be brief.')

    from app.ai import get_system_prompt
    assert get_system_prompt() == 'Be brief.'


def test_stream_no_provider(monkeypatch):
    """Kein Provider → Error-Event + DONE."""
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    monkeypatch.delenv('OLLAMA_BASE_URL', raising=False)

    from app.ai import stream_ai_response
    chunks = list(stream_ai_response('test'))

    assert any('Error' in c for c in chunks)
    assert 'data: [DONE]\n\n' in chunks
