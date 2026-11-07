import nltk
from collections import Counter
from nltk.stem import PorterStemmer


nltk.download('punkt_tab')


# Created this class to maybe help store important info?
# Will implement once we know what to store
# Since current implementation obviously takes too much memory
class Document:
    docu_id: int
    title: str
    text: str
    token_counts: Counter
    stem_token_counts: Counter
    unique_stem_tokens: list[str]
    scores: list[float]
    


# This class is so ugly sorry
class Tokenizer:
    def __init__(self):
        self.stemmer = PorterStemmer()

    # Can also use a simple split() call for this assignment
    def tokenize(self, text: str) -> list[str]:
        return nltk.word_tokenize(text)

    def get_token_counts(self, text: str) -> Counter:
        return Counter(self.tokenize(text))

    def stem(self, word_counts: Counter) -> Counter:
        stemmed_counts = Counter()
        for token, count in word_counts.items():
            stemmed_token = self.stemmer.stem(token)
            stemmed_counts[stemmed_token] += count
        return stemmed_counts

    # Returns Counter of stemmed token counts for text, useful for scoring
    def process(self, text: str) -> Counter:
        return self.stem(self.get_token_counts(text))

    # Returns list of unique stemmed tokens for text, useful for inverted index
    def process_unique(self, text: str) -> list[str]:
        return list(self.process(text).keys())
