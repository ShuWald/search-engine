import nltk
from collections import Counter
from nltk.stem import PorterStemmer

class Tokenizer:
    def __init__(self):
        nltk.download('punkt_tab')
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

    def process(self, text: str) -> Counter:
        return self.stem(self.get_token_counts(text))
