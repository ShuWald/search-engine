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

    if not args.f and os.path.isfile(args.index):
        print("Index already exists, -f to override.")
        return

    index = InvertedIndex(args.index)
    num_files = 0
    try:
        for dir in args.dirs:
            num_files += index.add_dir(dir)
    except KeyboardInterrupt:
        print("Indexing interrupted by user.")
    except Exception as e:
        print(f"Exception occurred: {e}")
    index.sync()
    print(f"Indexed {num_files} files total.")

main()
