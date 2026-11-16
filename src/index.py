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
    return [dirs / f for f in sorted(os.listdir(dirs)) if f.endswith(end)]

def chunk(name: str, xs: list) -> tuple[list[str], list[list]]:
    k = k_chunksize
    return ([f"{name}-{r}" for r in range(0, len(xs), k)], [xs[n*k: (n+1)*k] for n in range(0, len(xs), k)])

def index_all(name: str, dirs: list[Path]):
    files = find_files(".json", dirs)
    names, chunks = chunk(name, files)
    name_chunks = [n+".chunk" for n in names]
    name_inverts = [n+".chunk" for n in names]
    name_index = name+".index"
    with Pool() as pool:
        print(f"Parsing {len(name_chunks)} of {k_chunksize} files.")
        pool.starmap(parse_chunk, zip(name_chunks, chunks))
        log.info(f"Inverting {len(name_chunks)} of {k_chunksize} files.")
        pool.starmap(invert_chunk, zip(name_inverts, name_chunks))
    log.info(f"Merging into {name_index}.")
    merge_inverts(name_index, name_inverts)
    log.info("Index complete.")

def parse_chunk(out, files):
    # write tokens/scores to file linearly
    pass

def invert_chunk(out, chunk):
    # invert chunk to be an index file
    pass

def merge_inverts(out, files):
    # TODO: shard
    # merge into out
    pass
