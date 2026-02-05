from embedding import HashEmbedder


def test_hash_embedder_dim():
    emb = HashEmbedder(16)
    vectors = emb.embed(["hello world"])
    assert len(vectors) == 1
    assert len(vectors[0]) == 16
