import argparse
import json
import logging

from ExecutionProcessor import ExecutionProcessor


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize job execution records.")
    parser.add_argument("input_file", help="Path to a JSON file containing a list of records")
    parser.add_argument("--verbose", action="store_true", help="Show warning logs")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING if args.verbose else logging.ERROR,
        format="%(levelname)s: %(message)s",
    )

    response = ExecutionProcessor().process(args.input_file)
    print(json.dumps(response.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
