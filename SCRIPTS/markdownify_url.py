import argparse
import sys

import requests
from markdownify import markdownify as md


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="URL to fetch and markdownify")
    parser.add_argument("--timeout", type=int, default=10, help="Request timeout seconds")
    args = parser.parse_args()

    response = requests.get(args.url, timeout=args.timeout)
    response.raise_for_status()
    markdown = md(response.text)
    sys.stdout.write(markdown)


if __name__ == "__main__":
    main()
