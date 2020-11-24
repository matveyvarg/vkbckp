from typing import Union
from functools import partial
import asyncio
from concurrent.futures import ThreadPoolExecutor


class MessagesWorker:
    """
    Keep info about messages length and write to file when it's necessary
    """

    messages = []
    filled_up = 0

    def __init__(self, chunk_size: int = 5, max_messages: Union[str, int] = 'all'):
        self.chunk_size = chunk_size
        self.max_messages = max_messages

    def _write_message(self, message):
        """
        Write to file
        :param message:
        :return:
        """
        with open('messagex.txt', 'a') as f:
            f.write(message)
            self.messages = []
            self.filled_up += self.chunk_size

    async def save_to_file(self):
        """
        Write to file in another tread
        :return:
        """
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor() as pool:
            write_message = "\n".join(map(str, self.messages))
            await loop.run_in_executor(pool, partial(self._write_message, write_message))

    async def add(self, message: str):
        """
        Add to messages and if len of messages more than chunk_size, write to file
        :param message:
        :return:
        """
        self.messages.append(message)
        if len(self.messages) == self.chunk_size or (self.filled_up + self.chunk_size) > self.max_messages:
            await self.save_to_file()
