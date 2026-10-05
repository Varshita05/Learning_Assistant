from learning_assistant import cli


def test_cli_starts_uvicorn_with_configured_host_and_port(monkeypatch):
    called = {}
    monkeypatch.setenv("HOST", "127.0.0.1")
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setattr(
        cli.uvicorn,
        "run",
        lambda app, host, port: called.update(app=app, host=host, port=port),
    )

    cli.main()

    assert called == {
        "app": "learning_assistant.main:app",
        "host": "127.0.0.1",
        "port": 9000,
    }