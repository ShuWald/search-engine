import time
import sys
from src.index import Index
from argparse import ArgumentParser
import os

def main():

    parser = ArgumentParser(description="Find hard matches for keywords.")
    parser.add_argument("index")
    parser.add_argument("words", nargs='*')

    args = parser.parse_args()

    if not any(args.index.endswith(a) for a in [".index", ".invert"]):
        print(f"File {args.index} doesn't have the right extension (.index or .invert).")
        return

    if not os.path.isfile(args.index):
        print(f"Index file {args.index} doesn't exist.")
        return

    try:
        index = Index(args.index)
    except Exception as e:
        print(e)
        print("Failed to open index file.")
        raise
        return

    try:
        t1 = time.perf_counter()
        postings = index.query(args.words)
        t2 = time.perf_counter()
        print(f"Found {len(postings)} results:")
        for p in postings:
            print(p)
        print(f"Found {len(postings)} results in {t2 - t1} s.")
    except KeyboardInterrupt:
        print("Query interrupted by user.")
    except Exception as e:
        print(f"Exception occurred: {e}")
        raise

main()
