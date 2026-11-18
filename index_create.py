import sys
from invertedindex import InvertedIndex
from argparse import ArgumentParser
import os

def main():

    parser = ArgumentParser(description="Create an index over some files.")
    parser.add_argument("index")
    parser.add_argument("dirs", nargs='*')
    parser.add_argument("-f", action="store_true")

    args = parser.parse_args()

    index_file = args.index if args.index.endswith(".index") else args.index + ".index"
    if not args.f and os.path.isfile(index_file):
        print("Index already exists, -f to override.")
        return

    if args.f:
        for path in (index_file, index_file.removesuffix(".index") + ".jsonl"):
            try:
                os.remove(path)
            except FileNotFoundError:
                pass

    index = InvertedIndex(index_file)
    num_files = 0
    try:
        for dir in args.dirs:
            # Doesn't execute?
            num_files += index.add_dir(dir)
    except KeyboardInterrupt:
        print("Indexing interrupted by user.")
    except Exception as e:
        print(f"Exception occurred: {e}")
        raise
    index.sync()
    index.transactional_analytical()
    print(f"Indexed {num_files} files total.")

main()
