import argparse
import sys
from pathlib import Path

from src.config import ACTION_AUTO
from src.converter import convert_files


def main(argv=None):
    parser = argparse.ArgumentParser(description="Local-only file to PDF converter.")
    parser.add_argument("input", nargs="+", help="One or more files to convert.")
    parser.add_argument("-o", "--output", default="output", help="Output directory.")
    args = parser.parse_args(argv)

    files = [Path(item) for item in args.input]
    try:
        summary = convert_files(files, args.output, ACTION_AUTO, log_callback=print)
    except Exception as exc:
        print(f"Could not start conversion: {exc}")
        return 1

    for result in summary.results:
        if result.success:
            for output in result.outputs:
                print(f"Created: {output}")
        else:
            print(result.message)
    return 0 if summary.ok else 2


if __name__ == "__main__":
    sys.exit(main())
