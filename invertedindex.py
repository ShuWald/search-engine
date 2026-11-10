import base64
from pathlib import Path
import logger
import hashlib
import json
import os
import multiprocessing as mp

from doc import Doc


class InvertedIndex:
    def __init__(self, file: str):
        self.file = file
        self.lock = mp.Lock()
        self.logger = logger.get_file_logger("Index", propagate=True)

        self.url_unhash: dict[str, str] = {}
        self.known_urls: set[str] = set()
        # TODO: binary format
        # self.word_offsets: dict[str, tuple[int, int, int]] = {} # word -> lo, hi, end
        self.writes: list[Doc] = [] # unsynced objects
        self.word_postings: dict[str, list[tuple[str, float]]] = {} # unsynced objects

        self._open(file)

    def _open(self, file: str):
        if not os.path.exists(file):
            self.logger.info("No save file, creating new index.")
            self.sync(force=True)
            return
        with open(file) as f:
            try:
                obj = json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to open the index file: {e}.")
                raise
            try:
                self.url_unhash = obj["url_unhash"]
                self.known_urls = set(obj["known_urls"])
                self.word_postings = obj["word_postings"]
                self.logger.info("Opened existing index.")
            except Exception as e:
                self.logger.error("Saved index file is invalid - has missing field.")
                raise

    def _hash(self, url) -> bytes:
        hash = hashlib.sha256(bytes(url, encoding='utf8')).digest()
        self.url_unhash
        return hash

    def add_dir(self, dir: str | Path, depth = 0) -> int:
        # TODO: optimize, parallelize
        dir = Path(dir)
        count = 0
        total_files = 0
        self.logger.info(f"entering {dir}")
        for f in os.listdir(dir):
            path = dir / f
            if f.endswith(".json"):
                with open(path) as content:
                    posting = Doc(json.load(content), self.logger)
                    # TODO: allow overwrite, but don't duplicate files
                    if posting.url in self.known_urls:
                        self.logger.info(f"Skipping duplicate url from {f}")
                    else:
                        self.add_doc(posting)
                        count += 1
                        total_files += 1
                        if count % 100 == 0:
                            self.sync()
            elif os.path.isdir(path):
                total_files += self.add_dir(path, depth=depth+1)
        self.sync()
        return total_files

    def add_doc(self, doc: Doc):
        with self.lock:
            self.writes.append(doc)

    def query(self, tokens: list[str]):
        with self.lock:
            bail = False
            for w in tokens:
                if w not in self.word_postings:
                    self.logger.info(f"Searched token not in index: {w}")
                    bail = True
            if bail: return []
            rows = [self.word_postings[w] for w in tokens]
            pos = [0 for _ in rows]
            done = False
            results = []
            steps = 0
            while not done:
                docids = [r[p][0] for r, p in zip(rows, pos)]
                print(docids)
                print(pos)
                min_doc = min(docids)
                if all(d == min_doc for d in docids):
                    results.append(min_doc)
                for i in range(len(pos)):
                    if docids[i] == min_doc:
                        pos[i] += 1
                for i in range(len(pos)):
                    if pos[i] >= len(rows[i]):
                        done = True
                steps += 1
                if steps % 100 == 0:
                    print(f"Taken {steps} out of {max(len(r) for r in rows)}")
            return results

    def sync(self, force=False):
        with self.lock:
            if len(self.writes) == 0 and not force:
                self.logger.info("Syncing - nothing to do.")
                return
            self.logger.info(f"Syncing logger with {len(self.writes)} new writes...")
            for posting in self.writes:
                hash = self._hash(posting.url).hex()
                if posting.url in self.known_urls:
                    self.logger.warning("Duplicate posting made it to sync stage.")
                else:
                    self.known_urls.add(posting.url)
                    self.url_unhash[hash] = posting.url
                    for word, weight in posting.wordweights.items():
                        if word not in self.word_postings:
                            self.word_postings[word] = []
                        self.word_postings[word].append((hash, weight))
            for word in self.word_postings:
                self.word_postings[word].sort(key=lambda hw: hw[0])
            tmpfile = self.file+".tmp"
            with open(tmpfile, "w") as f:
                obj = {
                    "url_unhash": self.url_unhash,
                    "known_urls": list(self.known_urls),
                    "word_postings": self.word_postings
                }
                json.dump(obj, f, indent=4)
            try:
                os.remove(self.file)
            except FileNotFoundError:
                pass
            os.rename(tmpfile, self.file)
            self.writes = []
        self.logger.info("Synced logger.")
