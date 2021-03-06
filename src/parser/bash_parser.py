from . import parser
import bs4 as bs
import json
import os
import logging
from itertools import islice, chain
import sqlite3 as sqlite


def batch(iterable, size):
    """
    Batch iterator
    batch('ABCDE', 3) yields ('ABC', 'DE')
    :param iterable: iterable
    :param size: every size is yielded
    :return:
    """
    sourceiter = iter(iterable)
    while True:
        batchiter = islice(sourceiter, size)
        yield chain([next(batchiter)], batchiter)


def make_url(appendix, bash_url='https://bash.im'):
    """
    Make url from appendix and bash_url
    :param appendix: iterable, (str, ...)
    :param bash_url:
    :return: str, bash_url+/index/+appendix
    """
    pages = []
    for a in appendix:
        pages.append(bash_url+'/index/'+str(a))

    return pages


class BashParser(parser.Parser):
    def __init__(self, pages, db=None):
        """
        Pages is list of url's which to parse
        :param pages: list of url's
        """
        super().__init__()
        self.db = db
        if db is not None:
            self.create_table()
        self.pages = pages


    def parse(self, batch_size):
        """
        Parse pages
        :param batch_size: number of pages to be saved in one json file
        :return: None
        """
        self.parse_batch(self.pages, batch_size)

    def create_table(self):
        self.db_conn = sqlite.connect(self.db)
        self.db_cursor = self.db_conn.cursor()
        self.db_cursor.execute("""
            CREATE TABLE IF NOT EXISTS jokes
            (id int, jokes text, likes text, date text)
        """)
        self.db_conn.commit()

    def insert_into_table(self, jokes):
        self.db_cursor.executemany("INSERT INTO jokes VALUES (?,?,?,?)",
                                   [(joke['id'], joke['text'], joke['likes'], joke['date']) for joke in jokes])
        self.db_conn.commit()

    def save_jokes(self, jokes, **params):
        if self.db is None:
            self.save_jokes_json(jokes, filepath=params['filepath'])
        else:
            self.save_jokes_sqlite(jokes=jokes)

    def save_jokes_sqlite(self, jokes):
        assert self.db is not None, "specify sqlite db"
        self.logger.log(logging.INFO, 'save jokes to sqlite')
        self.insert_into_table(jokes)

    def save_jokes_json(self, jokes, filepath):
        """
        Save all jokes to json file
        :param filepath: path to save
        :param jokes: list of dict
        :return: None
        """
        with open(filepath, 'w') as f:
            self.logger.log(logging.INFO, 'save to {0}'.format(filepath))
            json.dump(jokes, f, ensure_ascii=False, separators=(',', ': '), indent=2)

    def parse_batch(self, pages_num, batch_size=100):
        """
        Parse pages and save every batch size
        :param pages_num: indices of page, list(int)
        :param batch_size: int,
        :return: None
        """
        assert isinstance(pages_num, (list, tuple)), "pages must be list or tuple, got {0}".format(type(pages_num))

        pages = make_url(pages_num)

        for i, pages_batch in enumerate(batch(pages, batch_size)):
            jokes = self.parse_pages(pages_batch)
            self.save_jokes(jokes)
            # self.save_page_jokes(os.path.relpath(f'./jokes/bash_jokes_{i}.json'), jokes)

    def parse_page(self, page_url):
        """
        Parse singel page
        :param page_url: str, page url like https://bash.im/index/2222
        :return: list of dict with text, id, likes, date
        """
        page = self.load_page(page_url)
        soup = bs.BeautifulSoup(page.text, "html.parser")
        quotes = soup.find_all('article', attrs={'class': ['quote']})

        jokes = []
        for quote in quotes:
            quote_total = quote.find('div', attrs={'class': ['quote__total']}).text
            text = quote.find('div', attrs={'class': ['quote__body']}).text.strip()
            quote_id = quote['data-quote']
            date = quote.find('div', attrs={'class': ['quote__header_date']}).text.strip().split(' в ')[0]
            quote_data = {
                'text': text,
                'id': quote_id,
                'likes': quote_total,
                'date': date
            }
            jokes.append(quote_data)
        self.logger.log(logging.INFO, f"jokes len {len(jokes)}")
        return jokes
