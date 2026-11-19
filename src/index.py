from pylab import ndarray
from collections import defaultdict, Counter
import json
from doc import Doc
import asyncio
import logger
import os
from typing import Iterable
from pathlib import Path
from multiprocessing import Process, Pool
import numpy as np

log = logger.get_file_logger("Index", propagate=True)

def flat(xss: list[Iterable]) -> list:
    out = []
    for xs in xss:
        out.extend(xs)
    return out

k_chunksize = 100

def find_files(end: str, dirs: list[Path] | Path) -> list[Path]:
    if isinstance(dirs, list):
        return flat([find_files(end, Path(d)) for d in sorted(dirs)])
    items = sorted(os.listdir(dirs))
    out = []
    for item in items:
        p = dirs / item
        if item.endswith(end):
            out.append(p)
        elif os.path.isdir(p):
            out.extend(find_files(end, p))
    return out

def chunk(name: str, xs: list) -> tuple[list[str], list[list]]:
    k = k_chunksize
    return ([f"{name}-{r}" for r in range(0, len(xs), k)], [xs[n: n+k] for n in range(0, len(xs), k)])

def index_all(name: str, dirs: list[Path]):
    files = find_files(".json", dirs)
    names, chunks = chunk(name, files)
    print(f"chunks are lengths {[len(c) for c in chunks]}")
    name_chunks = [n+".chunk" for n in names]
    name_inverts = [n+".invert" for n in names]
    name_index = name+".index"
    with Pool() as pool:
        print(f"Parsing {len(name_chunks)} chunks of {k_chunksize} files.")
        pool.starmap(parse_chunk, list(zip(name_chunks, chunks, [log]*len(name_chunks))))
        log.info(f"Inverting {len(name_chunks)} chunks of {k_chunksize} files.")
        pool.starmap(invert_chunk, zip(name_inverts, name_chunks, [log]*len(name_chunks)))
    log.info(f"Merging into {name_index}.")
    merge_inverts(name_index, name_inverts)
    log.info("Index complete.")

def cleanup(name):
    # TODO: delete chunks/inverts
    pass

def parse_chunk(name: str, files: list[Path], log):
    # write tokens/scores to file linearly
    already_read: set[str] = set()
    if os.path.exists(name):
        with open(name, "r") as f:
            for line in f:
                try:
                    already_read.add(json.loads(line)[0])
                except KeyboardInterrupt:
                    raise
                except Exception:
                    log.error(f"Failed to read chunk file, regenerating.")
                    os.remove(name)
                    already_read = set()
    with open(name, "a") as f:
        for file in files:
            if file.as_posix() in already_read:
                continue
            with open(file) as content:
                try:
                    doc = Doc(json.load(content))
                    wordweights: dict[str, int] = doc.wordweights
                    json.dump([file.as_posix(), doc.url, wordweights], f, indent=None, separators=(',', ':'))
                    f.write("\n")
                except KeyboardInterrupt:
                    raise
                except ValueError as e:
                    log.error(f"Found error during parsing: {e}")
    log.info(f"Completed chunk.")


"""
Inverted index has such format:
    jsons offset (8 bytes)
    postings list [doc_id, score] (2x4 bytes)
    term locations { term: offset } \n
    doc ids { url : doc_id }
"""
def invert_chunk(out, chunk, log):
    # invert chunk to be an index file
    doc_ids: dict[str, int] = {}
    word_postings: dict[str, list[tuple[int, int]]] = defaultdict(lambda: [])
    with open(chunk, "r") as f:
        for line in f:
            line = json.loads(line)
            wordweights: dict[str, int]
            _, url, wordweights = line
            doc_id = doc_ids[url] = len(doc_ids)
            for word, weight in wordweights.items():
                word_postings[word].append((doc_id, weight))
    term_locs: dict[str, int] = {}
    x = bytes()
    words = sorted(word_postings.keys())
    int_width = 2
    postings_length = sum(len(postings) * int_width * 2 for postings in word_postings.values())
    offset_index = 8 + postings_length
    pos = 8
    with open(out, "wb") as f:
        f.write(offset_index.to_bytes(8))
        for word in sorted(word_postings.keys()):
            term_locs[word] = pos
            # TODO: write via numpy buffer
            for posting in word_postings[word]:
                f.write(posting[0].to_bytes(int_width))
                f.write(posting[1].to_bytes(int_width))
            pos += len(word_postings[word]) * int_width * 2
        assert pos == offset_index, f"{pos} == {offset_index}"
        f.write(json.dumps(term_locs).encode())
        f.write("\n".encode())
        f.write(json.dumps(doc_ids).encode())
    log.info(f"Completed invert.")

def merge_inverts(out, files):
    # TODO: shard
    # merge into out
    n = len(files)
    indices = [Index(file) for file in files]

    num_docs = 0
    all_doc_ids: dict[str, int] = {} # map chunk -> doc id -> new doc id
    all_doc_urls: dict[int, str] = {} # map chunk -> doc id -> new doc id
    ind_doc_id: list[dict[int, int]] = [] # map chunk -> doc id -> new doc id
    all_terms: set[str] = set()
    for ind in indices:
        ind_doc_id.append({})
        i = len(ind_doc_id)-1
        for doc, url in ind.doc_urls.items():
            if doc in all_doc_ids:
                new_id = all_doc_ids[url]
            else:
                all_doc_ids[url] = num_docs
                new_id = num_docs
                all_doc_urls[new_id] = url
                num_docs += 1
            ind_doc_id[i][doc] = new_id
        all_terms.update(ind.term_ranges.keys())
    all_terms: list[str] = list(all_terms)

    dt = np.dtype([('id', '>H'), ('score', '>H')])
    term_postings: list[tuple[str, list]] = []
    has_duplicates = 0
    for term in sorted(all_terms):
        postings: list = []
        for i in range(n):
            doc_map = ind_doc_id[i]
            postings.extend([(doc_map[kv['id']], kv['score']) for kv in indices[i]._postings(term)])
        # postings = np.concat(*postings_lists, dtype=Index.dt)
        postings.sort(key=lambda k: k[0])
        if not has_duplicates:
            counts = Counter([p[0] for p in postings])
            for doc, count in counts.items():
                if count > 1:
                    print(f"Duplicate doc ids found for {all_doc_urls[doc]}")
                # has_duplicates = True
        term_postings.append((term, postings))

    int_width = 2
    json_offsets = 8 + sum(len(ps[1]) for ps in term_postings) * int_width * 2
    term_locs: dict[str, int] = {}
    pos = 8
    with open(out, "wb") as f:
        f.write((json_offsets).to_bytes(8))
        for term, postings in term_postings:
            term_locs[term] = pos
            for doc_id, score in postings:
                f.write(int(doc_id).to_bytes(int_width))
                f.write(int(score).to_bytes(int_width))
                pos += int_width * 2
        f.write(json.dumps(term_locs).encode())
        f.write("\n".encode())
        f.write(json.dumps(all_doc_ids).encode())




class Index:
    dt = np.dtype([('id', '>H'), ('score', '>H')])

    def __init__(self, filename):
        self.filename = filename
        self.term_ranges: dict[str, tuple[int, int]]
        self.doc_urls: dict[int, str]
        self._open()

    def _open(self):
        self.file = open(self.filename, "rb")
        f = self.file
        json_index = int.from_bytes(f.read(8))
        f.seek(json_index)
        line1 = f.readline()
        term_locs = sorted(json.loads(line1).items(), key=lambda x: x[1])
        next_locs = sorted([t[1] for t in term_locs])[1:] + [json_index]
        self.term_ranges = { kv[0]: (kv[1], r) for kv, r in zip(term_locs, next_locs) }
        line2 = f.readline()
        self.doc_urls = { i: doc for doc, i in json.loads(line2).items() }
        self.num_docs: int = len(self.doc_urls)
        # TODO: cache common words?

    def _postings(self, token: str) -> np.ndarray:
        if token not in self.term_ranges:
            return np.array([], dtype=self.dt)
        r = self.term_ranges[token]
        m = (r[1]-r[0])//self.dt.itemsize
        self.file.seek(r[0])
        return np.fromfile(self.file, count=m, dtype=self.dt)

    def query(self, tokens: list[str]) -> list[tuple[str, list[float]]]:
        if len(tokens) == 0:
            return []
        doc_ids = [self._postings(tok) for tok in tokens]
        locs = [0 for _ in doc_ids]
        maxs = [len(ds) for ds in doc_ids]
        f = self.file

        pos = 0
        result: list[tuple[str, list[float]]] = []
        min_id = 0
        while all(l < m for l, m in zip(locs, maxs)):
            # TODO: broken on multiple input
            min_id = min(ds[l]['id'] for ds, l in zip(doc_ids, locs))
            if all(ds[l]['id'] == min_id for ds, l in zip(doc_ids, locs)):
                result.append((self.doc_urls[min_id], list(ds[l]['score'] for ds, l in zip(doc_ids, locs))))
                for i in range(len(locs)):
                    locs[i] += 1
            else:
                # TODO: optimize by increment until cur max
                for i in range(len(locs)):
                    if doc_ids[i][locs[i]]['id'] == min_id:
                        locs[i] += 1
        return result
