from bs4 import BeautifulSoup
import requests
import re
from typing import Optional

class Scrapper:
    
    __SEARCH_URL = "https://www.google.com/search"
    __HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
    }

    def __init__(self, params: Optional[dict] = None):
        self.params = {} if params is None else params

    def __call__(self, *args, **kwargs) -> str:
        return self.get(*args, **kwargs)

    def get(self, q, params: Optional[dict] = None, max_words: int = 512) -> str:
        if params is None:
            params = self.params.copy()
        
        params.update({'q': q})

        results = self.__get_search_result(params)
        
        if (answer := self.__get_answer_if_available(results)) is not None:
            return self.__short_text(answer, max_words)

        links = self.__get_website_links(results)
        
        return self.__scrape_websites(links, max_words)

    def __short_text(self, text: str, max_words: int) -> str:
        return ' '.join(re.split('\W', text)[:max_words])
    
    def __get_search_result(self, params):
        html = requests.get(self.__SEARCH_URL, params=params, headers=self.__HEADERS, timeout=30)
        soup = BeautifulSoup(html.text, 'html.parser')
        return soup

    def __get_answer_if_available(self, soup) -> str | None:
        # with open('text.html', 'wb') as f:
        #     f.write(soup.prettify('utf-8'))
        result_box = soup.find('div', class_='v7W49e')
        if result_box is None:
            return None

        result_divs = result_box.find_all('div')
        first_result = result_divs[0]

        if 'ULSxyf' not in first_result.get('class', []):
            return None

        return ' '.join(first_result.stripped_strings)

    def __get_website_links(self, soup) -> list[str]:
        links = []
        for website in soup.select(".tF2Cxc"):
            links.append(website.select_one(".yuRUbf a")["href"])
        
        return links

    def __scrape_websites(self, links: list[str], max_words: int) -> str:
        words = []
        while len(words) < max_words and links:
            link = links.pop()
            response = requests.get(link)
            soup = BeautifulSoup(response.text, 'html.parser')
            text = soup.get_text()

            normalized_text = re.sub(r' +', r' ', text)
            words += normalized_text.split()
        
        return self.__short_text(' '.join(words), max_words)


if __name__ == "__main__":
    scrapper = Scrapper()
    queries = [
        "Who is president of USA?",
        "price of ETH",
        "locality sensitive hashing",
        "What is the weather",
        "weather Prague, hl. mesto"
    ]
    for q in queries:
        print(f'Query: {q}')
        print(f'Answer: {scrapper(q)}')
        print()