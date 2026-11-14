from nltk import PorterStemmer, word_tokenize
from invertedindex import InvertedIndex

class Search:
    def __init__(self, file):
        self.index = InvertedIndex(file)
        self.stemmer = PorterStemmer()

    def search(self, query):
        toks = word_tokenize(query)
        syms = [self.stemmer.stem(tok) for tok in toks]
        urls = self.index.query(syms)
        return urls
