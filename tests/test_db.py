from app.db import get_engine


def test_get_engine_returns_cached_instance():
    engine_one = get_engine()
    engine_two = get_engine()

    assert engine_one is engine_two
