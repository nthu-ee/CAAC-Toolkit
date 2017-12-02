import os
from .Year import Year


class ProjectConfig():

    __script_dir__ = os.path.dirname(os.path.abspath(__file__))

    # followings are adjust-able
    ROOT_DIR = os.path.join(__script_dir__, '..')
    DATA_DIR = os.path.join(ROOT_DIR, 'data')
    CRAWLER_RESULT_DIR = os.path.join(DATA_DIR, 'crawler_{}')
    CRAWLED_DB_FILENAME = 'sqlite3.db'

    @classmethod
    def getCrawledDbFilepath(self, year):
        """ Get the crawled db file for a sepecific year. """

        year = Year.taiwanize(year)

        return os.path.join(
            self.CRAWLER_RESULT_DIR.format(year),
            self.CRAWLED_DB_FILENAME,
        )
