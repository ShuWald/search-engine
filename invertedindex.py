from logging import Logger
import base64
from pathlib import Path
import logger
import hashlib
import json
import os
import multiprocessing as mp
import asyncio

from doc import Doc


class InvertedIndex:
    k_chunksize = 100

    def __init__(self, file: str | Path, tmp=False):
        self.file = Path(file)
        self.tmp = tmp
        self.lock = mp.Lock()
        self.logger = logger.get_file_logger("Index", propagate=True)

        self.url_unhash: dict[str, str] = {}
        self.known_urls: set[str] = set()
        # TODO: binary format
        # self.word_offsets: dict[str, tuple[int, int, int]] = {} # word -> lo, hi, end
        self.writes: list[Doc] = [] # unsynced objects
        self.word_postings: dict[str, list[tuple[str, float]]] = {} # unsynced objects

        self._open(file)

    def _open(self, file: str | Path):
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

    def __del__(self):
        if self.tmp:
            os.remove(self.file)

    def _hash(self, url) -> bytes:
        hash = hashlib.sha256(bytes(url, encoding='utf8')).digest()
        self.url_unhash[hash.hex()] = url
        return hash

    @staticmethod
    def _load_doc(file: Path, logger: Logger) -> Doc:
        with open(file) as content:
            return Doc(json.load(content), logger)

    async def _add_chunk(self, files: list[Path]) -> int:
        # TODO: create another index here temporarily?
        docs = [self._load_doc(file, self.logger) for file in files]
        # docs = await asyncio.gather(*[asyncio.to_thread(self._load_doc, f, self.logger) for f in files])
        counts = 0
        for file, doc in zip(files, docs):
            if doc.url in self.known_urls:
                self.logger.info(f"Skipping duplicate url from {file}")
            else:
                self.add_doc(doc)
                counts += 1
        if len(files) >= self.k_chunksize:
            self.sync()
        return counts

    # @staticmethod
    # async def _for_dir(dir: Path) -> int:
    #     index = InvertedIndex(dir / "tmp.index", tmp=True)

    @staticmethod
    async def _add_dir(self, dir: Path, depth: int) -> int:
        # TODO: optimize, parallelize
        self.logger.info(f"entering {dir}")
        contents = os.listdir(dir)
        files = [dir / c for c in contents if c.endswith(".json")]
        dirs = [dir / c for c in contents if not c.endswith(".json") and os.path.isdir(dir / c)]
        k = InvertedIndex.k_chunksize
        chunks = [files[n:n+k] for n in range(0, len(files), k)]

        fresh_count = 0
        # indices = [InvertedIndex(d / "tmp.index") for d in dirs]
        # for d in dirs:
        #     fresh_count += await self._add_dir(self, d, depth+1)
        fresh_count += sum(await asyncio.gather(*[self._add_dir(self, d, depth+1) for d in dirs]))
        # with mp.Pool() as pool:
            # res = pool.starmap(self._add_dir, [(index_dir[0], index_dir[1], depth+1) for index_dir in zip(indices, dirs)])
            # print("pool result is", res)
        # fresh_count += sum(res)

        # TODO: binary merge for O(n log n)
        # for i in range(1, len(indices)):
            # indices[0] = indices[0].union(indices[i])
        fresh_count += sum(await asyncio.gather(*[self._add_chunk(c) for c in chunks]))
        return fresh_count

    def add_dir(self, dir: str | Path) -> int:
        dir = Path(dir)
        counts = asyncio.run(self._add_dir(self, dir, depth=0))
        self.sync()
        return counts

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
            return [self.url_unhash[r] for r in results]

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
            tmpfile = self.file.as_posix() + ".tmp"
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
