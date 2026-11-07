import json

class InvertedIndex:
    def __init__(self):
        self.index = {}

    def add_document(self, doc_id: int, unique_tokens: list[str]):
        for token in unique_tokens:
            if token not in self.index:
                self.index[token] = []
            self.index[token].append(doc_id)

    def save_index(self):
        with open("inverted_index.json", "w") as f:
            json.dump(
                {k: sorted(v) for k, v in self.index.items()},
                f,
                indent=4
            )