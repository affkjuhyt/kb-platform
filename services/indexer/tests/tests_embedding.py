from services.embedding import SentenceTransformerEmbedder


def test_sentence_transformer_dim():
    # This will download the model if not cached
    emb = SentenceTransformerEmbedder(
        model_name="paraphrase-multilingual-MiniLM-L12-v2", dim=384
    )
    vectors = emb.embed(["hello world"])
    assert len(vectors) == 1
    assert len(vectors[0]) == 384
