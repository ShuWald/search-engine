from collections import defaultdict
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
    pass



class Index:
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
        print(f"Opened {len(self.doc_urls)} docs to search.")
        # TODO: cache common words?

    def query(self, tokens: list[str]) -> list[tuple[str, list[float]]]:
        ranges = [self.term_ranges[token] for token in tokens]
        locs = [0 for r in ranges]
        dt = np.dtype([('id', '>H'), ('score', '>H')])
        maxs = [(r[1]-r[0])//dt.itemsize for r in ranges]
        f = self.file
        doc_ids = []
        print("ranges are", ranges)
        for r, m in zip(ranges, maxs):
            f.seek(r[0])
            doc_ids.append(np.fromfile(f, count=m, dtype=dt))
            print(f"reading from {r[0]} to count {m}")
        print(doc_ids)

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
