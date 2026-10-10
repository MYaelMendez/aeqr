from ae import registry as r


def test_registry_loads_and_validates():
    data = r.load()
    assert data["version"]
    assert len(data["resources"]) == 277


def test_scopes_are_valid_and_ids_unique():
    rs = r.resources()
    assert all(x.scope in r.SCOPES for x in rs)
    ids = [x.id for x in rs]
    assert len(ids) == len(set(ids))


def test_public_only_resolves_to_https():
    for x in r.resources():
        if x.scope == "public":
            assert x.route.startswith("https://")


def test_local_resolves_to_ae_scheme():
    for x in r.resources():
        if x.scope == "local":
            assert x.route.startswith("ae://local/")


def test_by_category_and_resolve():
    scenes = r.by_category("threejs_scenes")
    assert len(scenes) == 8
    one = scenes[0]
    assert r.resolve(one.id) is not None
    assert r.resolve("does-not-exist") is None


def test_counts_total_matches():
    assert sum(r.counts().values()) == 277
