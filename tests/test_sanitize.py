"""S2 日志脱敏测试。"""

from core.agent.sanitize import sanitize_record, sanitize_value


def test_redact_api_key_in_string():
    raw = "key=sk-abcdefghijklmnopqrstuvwxyz123456"
    out = sanitize_value(raw)
    assert "[REDACTED]" in out
    assert "sk-abc" not in out


def test_sanitize_record_nested():
    record = {
        "event": "tool_result",
        "content": "DASHSCOPE_API_KEY=sk-secretkey12345678",
        "args": {"command": "echo sk-test1234567890abcdef"},
    }
    clean = sanitize_record(record)
    assert "sk-secret" not in str(clean)
    assert "sk-test" not in str(clean)
