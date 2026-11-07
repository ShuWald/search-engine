class Scorer:
    def __init__(self):
        pass

    def score(self, result: dict[str, int]) -> dict[str, float]:
        token_scores = {}
        # Score = basic frequency of tokens
        # This is stupid scoring and doesn't take into account stopwords/word importance
        word_count = sum(result["content"].values())
        for token, count in result["content"].items():
            token_scores[token] = count / word_count

        # Basic bonus score for title matching
        if result["title"] is not None:
            for token, count in result["title"].items():
                token_scores[token] += count / word_count

        return token_scores