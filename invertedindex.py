from logging import Logger
from pathlib import Path
import logger
import hashlib
import json
import os
import multiprocessing as mp
import asyncio

from doc import Doc


class InvertedIndex:
    k_chunksize = 1000

    def __init__(self, file: str | Path, tmp=False):
        passed_file = Path(file)
        if passed_file.suffix == ".index":
            self.index_file = passed_file
            self.records = passed_file.with_suffix(".jsonl")
        else:
            self.records = passed_file if passed_file.suffix == ".jsonl" else passed_file.with_suffix(".jsonl")
            self.index_file = passed_file.with_suffix(".index")
        self.tmp = tmp
        self.lock = mp.RLock()
        self.logger = logger.get_file_logger("Index", propagate=True)

        self.url_unhash: dict[str, str] = {}
        self.known_urls: set[str] = set()
        # TODO: binary format
        # self.word_offsets: dict[str, tuple[int, int, int]] = {} # word -> lo, hi, end
        self.writes: list[Doc] = [] # unsynced objects
        self.word_postings: dict[str, list[tuple[str, float]]] = {} 

        self._open(file)

    def _open(self, file: str | Path):
        if not os.path.exists(self.records) and not self.index_file.exists():
            self.logger.info("No save file, creating new index.")
            self.sync(force=True)
            return
        if self.index_file.exists():
            try:
                with open(self.index_file, encoding="utf-8") as f:
                    obj = json.load(f)
                self.url_unhash = obj["url_unhash"]
                self.known_urls = set(obj["known_urls"])
                self.word_postings = {
                    word: [tuple(posting) for posting in postings]
                    for word, postings in obj["word_postings"].items()
                }
                self.logger.info(
                    f"Opened analytical index with {len(self.known_urls)} documents."
                )
                if os.path.exists(self.records) and not self._analytical_is_current():
                    self.transactional_analytical()
                return
            except (OSError, KeyError, TypeError, json.JSONDecodeError, ValueError):
                self.logger.warning("Analytical index is invalid; rebuilding it.")
        if os.path.exists(self.records):
            self.transactional_analytical()
            self.logger.info(
                f"Opened rebuilt index with {len(self.known_urls)} documents."
            )
            return
        self.logger.error("Neither transactional nor analytical index data exists.")

    def __del__(self):
        if self.tmp:
            for path in (self.records, self.index_file):
                try:
                    os.remove(path)
                except FileNotFoundError:
                    pass

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
        if len(self.writes) >= self.k_chunksize:
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

    def _analytical_is_current(self) -> bool:
        try:
            if not self.index_file.exists():
                return False
            if not self.records.exists():
                return True
            # Compare the analytical snapshot and final transactional row.
            # Note: if transactional is reverted to an older, shorter state, the mismatch currently causes rebuilt; 
            # can be easily fixed by comparing doc_id against analytical word posting doc_id lists instead
            with open(self.index_file, encoding="utf-8") as f:
                analytical = json.load(f)
            last_line = None
            with open(self.records, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        last_line = line
            if not last_line:
                return True
            last_row = json.loads(last_line)
            last_doc_id = hashlib.sha256(
                bytes(last_row["url"], encoding="utf8")
            ).hexdigest()
            return (
                analytical.get("last_doc_id") == last_doc_id
            )
        except (OSError, KeyError, TypeError, json.JSONDecodeError):
            return False

    def query(self, tokens: list[str]):
        with self.lock:
            if not tokens:
                return []
            if not self._analytical_is_current():
                self.transactional_analytical()
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
                    self.logger.debug(f"Taken {steps} out of {max(len(r) for r in rows)}")
            return [self.url_unhash[r] for r in results]

    def sync(self, force=False):
        with self.lock:
            if len(self.writes) == 0 and not force:
                self.logger.info("Syncing - nothing to do.")
                return
            self.logger.info(f"Syncing logger with {len(self.writes)} new writes...")
            rows = []
            for posting in self.writes:
                doc_id = self._hash(posting.url).hex()
                if posting.url in self.known_urls:
                    self.logger.warning("Duplicate posting made it to sync stage.")
                    continue

                rows.append({
                    "doc_id": doc_id,
                    "url": posting.url,
                    "wordweights": posting.wordweights,
                })
                self.known_urls.add(posting.url)
                self.url_unhash[doc_id] = posting.url
                for word, weight in posting.wordweights.items():
                    self.word_postings.setdefault(word, []).append((doc_id, weight))

            if rows:
                with open(self.records, "a", encoding="utf-8") as f:
                    for row in rows:
                        f.write(json.dumps(row) + "\n")
                    f.flush()
                    os.fsync(f.fileno())
            for word in self.word_postings:
                self.word_postings[word].sort(key=lambda hw: hw[0])

            self.writes = []
        self.logger.info("Synced logger.")

    def transactional_analytical(self):
        with self.lock:
            # Rebuild both in-memory posting state and the analytical snapshot.
            self.word_postings = {}
            self.known_urls = set()
            self.url_unhash = {}
            last_doc_id = None
            with open(self.records, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    doc_id = hashlib.sha256(
                        bytes(row["url"], encoding="utf8")
                    ).hexdigest()
                    last_doc_id = doc_id
                    self.known_urls.add(row["url"])
                    self.url_unhash[doc_id] = row["url"]
                    for word, weight in row["wordweights"].items():
                        self.word_postings.setdefault(word, []).append((doc_id, weight))

            for postings in self.word_postings.values():
                postings.sort(key=lambda posting: posting[0])

            temporary_file = self.index_file.with_suffix(".tmp")
            with open(temporary_file, "w", encoding="utf-8") as f:
                json.dump({
                    "last_doc_id": last_doc_id,
                    "url_unhash": self.url_unhash,
                    "known_urls": list(self.known_urls),
                    "word_postings": self.word_postings,
                }, f, indent=4)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporary_file, self.index_file)
            self.logger.info("Updated analytical word postings.")

# possible function (don't implement): analytical_transactional
# I really dont see the point unless we only really want to keep one file
# (and we're sure that we wont ever have to rebuild index, but an exception occurs)