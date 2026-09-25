from app.db import short_id


def test_short_ids_are_unique_and_resolve_case_insensitively():
    ids = {short_id.generate() for _ in range(2000)}
    assert len(ids) == 2000
    for sid in list(ids)[:50]:
        assert len(sid) == 8 and set(sid) <= set(short_id.ALPHABET)
        assert short_id.normalise(sid.lower()) == sid
        assert short_id.normalise(f" {sid[:4]}-{sid[4:]} ") == sid
    assert short_id.normalise("7k3qxi1o") == "7K3QX110"
    assert short_id.normalise("7K3QXLLO") == "7K3QX110"
    assert short_id.normalise("7K3QX9M") is None
    assert short_id.normalise("7K3QX9MU") is None
    assert short_id.normalise("") is None
