#!/usr/local/python310/bin/python3.10
import asyncio
import logging
import os
import telnetlib3

from wordle.wordle import game



def main():
    loop = asyncio.get_event_loop()
    coro = telnetlib3.create_server(port=6023, shell=game)
    server = loop.run_until_complete(coro)
    loop.run_until_complete(server.wait_closed())


if __name__ == "__main__":
    if os.environ.get("DEBUG"):
        logging.basicConfig(level=logging.DEBUG)

    main()
