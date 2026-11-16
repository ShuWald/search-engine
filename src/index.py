import json
from doc import Doc
import asyncio
import logger
import os
from typing import Iterable
from pathlib import Path
from multiprocessing import Process, Pool

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
        pool.starmap(invert_chunk, zip(name_inverts, name_chunks))
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
                    json.dump([file.as_posix(), wordweights], f, indent=None, separators=(',', ':'))
                    f.write("\n")
                except KeyboardInterrupt:
                    raise
                except ValueError as e:
                    log.error(f"Found error during parsing: {e}")
    log.info(f"Completed chunk.")


def invert_chunk(out, chunk):
    # invert chunk to be an index file
    pass

def merge_inverts(out, files):
    # TODO: shard
    # merge into out
    pass
