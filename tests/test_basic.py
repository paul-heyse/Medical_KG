from Medical_KG import ping


def test_ping():
    assert ping() == "pong"
