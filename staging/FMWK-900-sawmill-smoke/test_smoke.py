def test_ping() -> None:
    from smoke import ping

    assert ping() == "pong"
