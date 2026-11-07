import json

class InvertedIndex:
    def __init__(self):
        self.index = {}

    def add_document(self, doc_id: int, token_counts: list[str]):
        for token, count in token_counts.items():
            if token not in self.index:
                self.index[token] = []
            self.index[token].append((doc_id, count))



    def save_index(self):
        with open("inverted_index.json", "w") as f:
            json.dump(
                {k: sorted(v) for k, v in self.index.items()},
                f,
                indent=4
            )