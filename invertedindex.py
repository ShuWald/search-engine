import json
import bisect
class InvertedIndex:
    def __init__(self):
        self.index = {}

    def add_document(self, doc_id: int, unique_tokens: list[tuple[str, int]]):
        for token, frequency in unique_tokens:
            if token not in self.index:
                self.index[token] = []
            # self.index[token].append(doc_id)
            bisect.insort(self.index[token], (doc_id, frequency), key=lambda x: x[0])

    def save_index(self):
        with open("inverted_index.json", "w") as f:
            json.dump(
                {k: sorted(v) for k, v in self.index.items()}, f, indent=4)