
import pathlib
import sys
from functools import cached_property

import scrapy
from scrapy.crawler import CrawlerRunner

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager

from multiprocessing import Process, Queue
from twisted.internet import reactor


class Screenshotter:

    def __init__(self, root, urls):
        self.root = root
        self.urls = urls

    @cached_property
    def options(self):
        options = Options()
        options.headless = True
        return options

    @cached_property
    def driver(self):
        return webdriver.Firefox(
            options=self.options,
            service=Service(executable_path=GeckoDriverManager().install()))

    @property
    def screenshots(self):
        screenshots = {}

        for url in self.urls:
            ss = self.take_screenshot(url)
            screenshots[ss] = pathlib.Path(ss).read_bytes()
        return screenshots

    def take_screenshot(self, url):
        self.driver.get(url)
        output = self.file_from_url(url)
        self.driver.get_full_page_screenshot_as_file(output)
        return output

    def exit(self):
        self.driver.quit()

    def file_from_url(self, url):
        filename = url[len(self.root) + 1:].replace("/", "__")
        return f"{filename}.png"


class DocsSpider(scrapy.Spider):
    name = 'docs'
    allowed_domains = ['storage.googleapis.com']
    custom_settings = {'ROBOTSTXT_OBEY': False}

    def __init__(self, commit_hash=None, collected=None):
        self.commit_hash = commit_hash
        self.collected = collected

    @cached_property
    def start_urls(self):
        return [f'https://storage.googleapis.com/envoy-pr/{self.commit_hash}/docs/api-v3/api.html']

    def parse(self, response):
        if not response.css("title") or "no title" in response.css("title")[0].get():
            yield {"bad": response.url}

        self.collected.add(response.url)

        for next_page in response.css('a'):
            link = next_page.xpath("./@href").extract()
            if not link or ".." in link[0] or "_sources" in link[0] or "#" in link[0] or link[0].startswith("https:"):
                continue
            # print(response.url)
            # print(link[0])
            yield response.follow(next_page, self.parse)


# To run twice we need to fork the process
def run_spider(spider, **kwargs):

    def f(q):
        collected_set = set()

        try:
            runner = CrawlerRunner()
            deferred = runner.crawl(spider, collected=collected_set, **kwargs)
            deferred.addBoth(lambda _: reactor.stop())
            reactor.run()
            q.put(collected_set)
        except Exception as e:
            q.put(e)


    q = Queue()
    p = Process(target=f, args=(q,))
    p.start()
    result = q.get()
    p.join()

    return list(sorted(r for r in result if r.endswith("proto.html")))


def collect_screenshots(commit_hash):
    screenshotter = Screenshotter(
        f"https://storage.googleapis.com/envoy-pr/{commit_hash}/docs/api-v3",
        run_spider(DocsSpider, commit_hash=commit_hash))
    return screenshotter.screenshots


def main():
    before_hash = sys.argv[1]
    after_hash = sys.argv[2]

    before_screenshots = collect_screenshots(before_hash)
    after_screenshots = collect_screenshots(after_hash)

    matched = []
    failed = []

    for k, v in before_screenshots.items():
        if v == after_screenshots[k]:
            matched.append(k)
        else:
            failed.append(k)

    for fail in failed:
        print(f"FAILED: {fail}", file=sys.stderr)

    print(f"TOTAL MATCHED: {len(matched)}", file=sys.stderr)
    print(f"TOTAL FAILED: {len(failed)}", file=sys.stderr)

    failed_dir = pathlib.Path("/failed")

    for k in failed:
        failed_item_dir = failed_dir.joinpath(k)
        failed_item_dir.mkdir()
        failed_before = failed_item_dir.joinpath("before.png")
        failed_before.write_bytes(before_screenshots[k])
        failed_after = failed_item_dir.joinpath("after.png")
        failed_after.write_bytes(after_screenshots[k])


if __name__ == "__main__":
    main()
