from pathlib import Path
import sys
from src.index import index_all
from argparse import ArgumentParser
import os

def main():

    parser = ArgumentParser(description="Create an index over some files.")
    parser.add_argument("index")
    parser.add_argument("dirs", nargs='*')
    parser.add_argument("-f", action="store_true")

    args = parser.parse_args()

    if not args.index.endswith(".index"):
        print("Index file should have .index extension.")
        return
    name = args.index[:-6]
    print(f"Using {name}.index")
    if not args.f and os.path.isfile(args.index):
        print("Index already exists, -f to override.")
        return
    if not os.path.exists(Path(args.index).parent):
        os.mkdir(Path(args.index).parent)

    try:
        index_all(name, [Path(d) for d in args.dirs])
    except KeyboardInterrupt:
        print("Indexing interrupted by user.")
    except Exception as e:
        print(f"Exception occurred: {e}")
        raise

if __name__ == "__main__":
    main()
