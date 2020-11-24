import argparse


def parse_args() -> dict:
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--login', required=True)
    parser.add_argument('-p', '--password', required=True)
    parser.add_argument('numbers_to_fetch', metavar='M', type=int)
    parser.add_argument('url', nargs='?', type=str)

    return vars(parser.parse_args())
