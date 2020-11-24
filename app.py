from typing import Iterator
from asyncio import get_event_loop

from pyppeteer import launch
from pyppeteer.page import Page, ElementHandle

from utils import parse_args
from worker import MessagesWorker


class App:
    """
    Main app class
    """
    FETCH_ALL = -1
    MESSAGE_BLOCK_SELECTOR = '.im-page--history'

    filled_ids = []
    worker = MessagesWorker(max_messages=10)

    def __init__(self, login: str, password: str, url: str, *args, **kwargs):
        """
        Sets config if exists and run methods
        :param args:
        :param kwargs:
        """
        assert login
        assert password
        assert url

        self.login = login
        self.password = password
        self.url = url

        # TODO: numbers to fetch cant be less than chunk size
        self.chunk_size = kwargs.get('chunk_size', 5)
        self.numbers_to_fetch = kwargs.get('numbers_to_fetch', -1)

        print("App started")
        self.run_app()

    def run_app(self):
        """
        Runs async app to fetch data from Pyppeteer
        :return:
        """
        loop = get_event_loop()
        loop.run_until_complete(self.start())

    async def start(self):
        """
        Fetch data from given chat and save it
        :return:
        """
        print("start")
        page = await self.run_pypeteer()
        await self.authorize(page)
        await self.fetch_messages(page)

    async def run_pypeteer(self) -> Page:
        """
        Creates browser object and goes to given url
        :return:
        """
        print("Pypeteer opening")
        browser = await launch()
        page = await browser.newPage()
        await page.goto(self.url)
        await page.waitForSelector('.top_home_logo')
        return page

    async def authorize(self, page: Page):
        print("authorize")

        await page.waitForSelector('#login_form')

        # Login
        await page.click('input[id="email"]')
        await page.keyboard.type(self.login)

        # Password
        await page.click('input[id="pass"]')
        await page.keyboard.type(self.password)

        # Click btn
        await page.click('button[id="login_button"]')
        await page.waitForSelector('.side_bar')

        await page.goto(self.url)
        await page.waitForSelector(self.MESSAGE_BLOCK_SELECTOR)

    async def proceed_messages(self, page: Page, messages: Iterator[ElementHandle]):
        """
        Loop through the messages and add it to worker
        :param page:
        :param messages:
        :return:
        """
        msg_counter = 0
        for message_element in messages:
            if self.numbers_to_fetch > 0 and msg_counter > self.numbers_to_fetch - self.worker.filled_up:
                break
            message = {
                'author': await message_element.querySelectorEval('.im-mess-stack--pname', '(el) => el.innerText')
            }

            # If there is reply, fill it
            reply = await message_element.querySelector('.im-replied')
            if reply:
                message['reply_text'] = await reply.querySelectorEval('.im-replied--text', '(el) => el.innerText')
                message['reply_author'] = await reply.querySelectorEval('.im-replied--author', '(el) => el.innerText')

                await page.evaluate('(el)=>el.remove()', reply)

            # Text of message
            message['text'] = "\n".join(
                await message_element.querySelectorAllEval('.im-mess--text', '(el) => el.map(i => i.innerHTML)'))
            text = "{:-^25}\n".format(message['author'])

            # Reply block
            if reply:
                text += "-{:^12}-\n".format(message['reply_author'])
                text += message['reply_text'] + "\n"
                text += "*" * 25 + '\n'

            # Main text
            text += message['text'] + '\n'
            text += "-" * 25 + '\n'
            print(text)
            await self.worker.add(text)
            msg_counter += 1

    async def get_elements(self, page: Page, breaker: str):
        elems = []
        msgid = None
        for i, elem in enumerate(await page.querySelectorAll(f'{self.MESSAGE_BLOCK_SELECTOR} .im-mess-stack--content')):
            elem_msgid = await elem.querySelectorEval('.im-mess', '(el)=>el.getAttribute("data-msgid")')

            if i == 0:
                msgid = elem_msgid

            if elem_msgid == breaker:
                break

            elems.append(elem)

        return reversed(elems), msgid

    async def fetch_messages(self, page: Page):
        """
        Get all messages by chunks
        :param page:
        :return:
        """
        print("messages")
        msgid = 'null'

        if self.numbers_to_fetch == self.FETCH_ALL:

            last_msg = None

            while True:
                elems, msgid = await self.get_elements(page, msgid)
                if msgid == last_msg:
                    break
                last_msg = msgid
                await self.proceed_messages(page, elems)
                await self.scroll(page)
        else:

            while self.worker.filled_up < self.numbers_to_fetch:
                elems, msgid = await self.get_elements(page, msgid)
                await self.proceed_messages(page, list(elems))
                await self.scroll(page)
                print(self.worker.filled_up, self.numbers_to_fetch)

    async def scroll(self, page: Page):
        await page.evaluate('() => document.querySelector(".im-page--history .ui_scroll_outer").scrollTop = 0')
        await page.screenshot({'path': 'i.png'})
        await page.waitFor(20000)

if __name__ == "__main__":
        app = App(**parse_args())
