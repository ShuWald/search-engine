import readline
import time
import os
from src.search import Search
from argparse import ArgumentParser

def main():
    parser = ArgumentParser(description="Search the index through the commandline.")
    parser.add_argument("index")
    parser.add_argument("query", nargs='*')
    parser.add_argument("-n", nargs=1, type=int, default=5)
    parser.add_argument("-q", action="store_true")

    args = parser.parse_args()

    if not any(args.index.endswith(a) for a in [".index", ".invert"]):
        print(f"File {args.index} doesn't have the right extension (.index or .invert).")
        return

    if not os.path.isfile(args.index):
        print(f"Index file {args.index} doesn't exist.")
        return

    try:
        t1 = time.perf_counter()
        search = Search(args.index)
        t2 = time.perf_counter()
        print(f"Opened Search in {t2 - t1:.4f} s")
    except Exception as e:
        print("Failed to open Search.")
        raise

    def ask(query):
        t1 = time.perf_counter()
        results = search.search(query)
        t2 = time.perf_counter()
        for r in results[:args.n]:
            print(f"    {r}")
        print(f"{len(results)} found in {t2 - t1 : .4f} s.")

    try:
        for query in args.query:
            print(f"> {query}")
            ask(query)
        if not args.q:
            while True:
                print("> ", end="")
                query = input().strip()
                if query in ["", "q", "quit", "exit"]:
                    print("Exiting.")
                    return
                if query != "":
                    ask(query)
    except (EOFError, KeyboardInterrupt) as e:
        print("Exiting.")
    except Exception as e:
        print(f"Exception occurred: {e}")
        raise

main()
