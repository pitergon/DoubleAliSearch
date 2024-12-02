import os
import asyncio
import json
import random
import re
from datetime import datetime
from typing import Optional

import httpx
from httpx import HTTPStatusError, RequestError
from bs4 import BeautifulSoup
from calmjs.parse import es5
from calmjs.parse.unparsers.extractor import ast_to_dict
from redis.asyncio import Redis


class SearchEngine:
    """
    Main class for searching products on Aliexpress
    """

    def __init__(self, session_id: str, search_uuid: str, redis: Redis):

        self.session_id = session_id
        self.search_uuid = search_uuid
        self.redis = redis
        self.task: Optional[asyncio.Task] = None  # Link to background task
        # self.queries_list = queries_list
        # self.messages_lock = messages_lock
        # self.messages = []
        # self.stop_flag = False
        # self.is_running = False
        self.base_url = 'https://www.aliexpress.com/w/wholesale'
        # Max number of result pages for parsing. After 8 pages results are often  not relevant
        self.max_page = 6
        # Max number of pages without new products in search result
        self.max_zero_pages = 2
        # Rechecking the product name for compliance with the search query
        self.filter_result = True
        self.enable_pause = False
        self.max_pause_time = 5
        self.use_fake_html = True
        self.enable_save_to_json = False

    async def check_stop_flag(self):
        entry = await self.redis.get(f"{self.session_id}:{self.search_uuid}:stop_flag")
        return bool(int(entry)) if entry else False

    @staticmethod
    def _get_fake_html(search: str, page_number: int = None) -> str:
        """
        Returns fake html from previously saved txt files

        :param search:
        :param page_number:
        :return:
        """

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        file_name = f"{search}-{page_number}.txt"
        file_path = os.path.join(BASE_DIR, "test_data", file_name)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                print(f"Read file {file_name}")
                html = f.read()
        except OSError as e:
            print(e)
            html = ''
        return html

    async def _get_html(self,
                        search: str,
                        page_number: int = None,
                        ) -> str:
        """
        Gets HTML from page with global search results
    
        :param search:
        :param page_number:
        :return:
        """

        if self.use_fake_html:
            self.max_page = 3
            return self._get_fake_html(search, page_number)

        url = f"{self.base_url}-{search.replace(" ", "-").lower()}.html"
        params = {
            'spm': 'a2g0o.home.search.0',
        }
        if page_number and page_number > 1:
            params["page"] = page_number

        cookies = {
            'ali_apache_id': '33.27.108.54.1723404130100.617835.3',
            'intl_locale': 'en_US',
            'xman_f': 'ucThPsuv3+lC89SvCHwqTCdL854B5E1ieBG6oDTwRN1ceTUmueNrMPrfSwJYhGjbvzMaI9sluzkkDaTzIF0xZqLCXPSV0qkaX6A7hFpatjtli/o1Id9yKg==',
            'acs_usuc_t': 'x_csrf=yxmcfi63yjf1&acs_rt=980b8afaffed4b7a8af98bddbc0c6534',
            'xman_t': 'LOFMSOzP81IKtPmbTj/In3BvOpim9o1qNNWptfPVjOFU0aNnOVPVYxZWlMN8pBij',
            'AKA_A2': 'A',
            'lwrid': 'AgGRQuQZqUXxbWOCpdUOX39uI6%2FK',
            'join_status': '',
            '_m_h5_tk': 'adccd53ae28e949142bcc05be23a18e8_1723406473036',
            '_m_h5_tk_enc': 'e31ce6ca50be394561ec69ea5ffd8b80',
            'ali_apache_track': '',
            'ali_apache_tracktmp': '',
            'e_id': 'pt70',
            'lwrtk': 'AAEEZrl/44/jQR/CXe1j+RZXlsIMqnIlxU3OyqGYxfSazrgSka0MGOo=',
            'cna': 'Zf0/H6rCtw4CAVqDLRHkBLc2',
            'AB_DATA_TRACK': '472051_617391',
            'AB_ALG': '',
            'AB_STG': 'st_StrategyExp_1694492533501%23stg_687',
            'aep_usuc_f': 'site=glo&c_tp=EUR&ups_d=1|1|1|1&ups_u_t=1738956388717&region=LT&b_locale=en_US&ae_u_p_s=2',
            '_gcl_au': '1.1.1586149601.1723404389',
            '_ga': 'GA1.1.1250008122.1723404382',
            '_ga_VED1YSGNC7': 'GS1.1.1723404381.1.1.1723404440.8.0.0',
            'isg': 'BLi4xkcMKqI-70YmrXroA-VxiWZKIRyrValO5PIpDvPSDVn3nTO1O-kvxR29XdSD',
            'xman_us_f': 'x_locale=en_US&x_l=0&x_c_chg=1&acs_rt=980b8afaffed4b7a8af98bddbc0c6534',
            'intl_common_forever': 'jRbrMvYq77NoV8HmjpgCftGx9o3O/i6FaGGXkjksqo3nRBX+l/vEqQ==',
            'epssw': '5*mmLjaRkX5AhOAWhKR9WnA4YaZOfnnXoUNWmK0CSzHmYsp1eCLKpRh32I0VMRVCW2N5H_1xxlHhxmmhHvCnhwSheoZV8Rh32IGzNRVCWFEBMt_HSfprCRbFl8x58aaGCRGLrq_HGjjLSdt23Uu2KBozfgFWE18FDSvS5m9LZYm38hI9QnNEmNayKNWgL6acYtv_pmrr_djW8dsRQms2Ux0RIHMBbK035iM5mj0C7X7YFGzJYlNnVwzFzr8J0EGPV17GhdsRem8QQ3fbVJb8gfP_Wv8ZF6lW3lMqnfPhLIfpmhyWQhrHrzrtvmmX8IUrgDzuz89_XPcJ6FmXN_xTNy4SsyiPLMkBQJ5LlDA7dw7WcommmmmUwebREsfViZmheNo1PzVVh.',
        }

        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'ru-RU,ru;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'priority': 'u=0, i',
            'referer': 'https://www.aliexpress.com/?spm=a2g0o.productlist.logo.1.3e6bGde2Gde2kT',
            'sec-ch-ua': '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
        }

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=10.0)) as client:
                client.cookies = cookies
                response = await client.get(
                    url,
                    params=params,
                    headers=headers,
                )
                response.raise_for_status()  # Raises an exception for 4xx/5xx responses
        except HTTPStatusError as e:
            msg = f"HTTP Error: {e.response.status_code}"
            await self.add_message(msg)
            return 'error'
        except RequestError as e:
            msg = f"Request Error: {str(e)}"
            await self.add_message(msg)
            return 'error'

        msg = f"Processing {response.url}"
        await self.add_message(msg)
        return response.text

    async def add_message(self, message: str):
        """
        Add message to message queue about search status
        :param message:
        :return:
        """

        time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        await self.redis.rpush(f"{self.session_id}:{self.search_uuid}:messages", f"{time_str} - {message}")
        print(f"{time_str} - {self.search_uuid[-4:]} - {message}")

    async def _get_next_page_number(self, soup: BeautifulSoup) -> int | str:
        """
        Returns number of next page
    
        :param soup:
        :return:
        """
        try:
            active_page = int(soup.find("li", class_="comet-pagination-item-active").text.strip())
            page_count = int(soup.find_all("li", class_="comet-pagination-item")[-1].text.strip())
        except (AttributeError, ValueError):
            msg = "Can't find next page number"
            await self.add_message(msg)
            return 'error'

        return active_page + 1 if active_page < page_count else 0

    async def _get_page_count(self, soup: BeautifulSoup):
        try:
            page_count = int(soup.find_all("li", class_="comet-pagination-item")[-1].text.strip())
        except (AttributeError, ValueError):
            msg = "Failed search numbers of page"
            await self.add_message(msg)
            return 'error'

        return page_count

    @staticmethod
    def _save_report_as_json(data: dict, report_name: str):
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(BASE_DIR, 'json_files', f'{report_name}.json')
        if len(filename) > 250:
            cut_symbols = len(filename) - 250
            report_name = report_name[:-cut_symbols]
            filename = os.path.join(BASE_DIR, 'json_files', f'{report_name}.json')
        with open(filename, 'w', encoding='utf-8') as f:
            # noinspection PyTypeChecker
            json.dump(data, f, ensure_ascii=False, indent=4)

    @staticmethod
    def _get_nested_dict_item(source: dict, *args, default=""):
        """
        Return value from nested dict
        :param source:
        :param args:
        :param default:
        :return:
        """

        d = source
        for a in args:
            try:
                d = d[a]
            except KeyError:
                return default
        return d

    @staticmethod
    def _is_relevant(src: str, search: str) -> bool:
        """
        The function checks that the string is relevant to the search query
        :param src: source string
        :param search: search
        :return: bool
        """
        src = src.lower()
        search = search.lower()
        words = search.split(' ')
        words.append(search.replace(' ', '-'))
        words.append(search.replace(' ', ''))
        for word in words:
            if src.find(word) >= 0:
                return True
        return False

    async def _get_script_items(self, script: str) -> dict | str:
        """
        Function searches in JSON array with products. Returns dictionary with product_info
        {
            "product_id": {
                    "product_id": product_id,
                    "title": title,
                    ...
                },
        }
    
        :param script:
        :return:
    
        First try to find part of string  and load it to JSON
        If it doesn't work, we use parsing the AST tree of the js script to access the variables
        """

        #  First try to find part of string  and load it to JSON

        pos_start = script.find('{"hierarchy"')
        json_str = script[pos_start:-1]
        item_list = {}
        products = {}
        try:
            json_list = json.loads(json_str)
            item_list = json_list["data"]["root"]["fields"]["mods"]["itemList"]["content"]
        except (json.JSONDecodeError, KeyError):
            msg = "Failed to get JSON from javascript with string methods"
            await self.add_message(msg)

        # If it doesn't work, we use parsing the AST tree of the js script to access the variables

        if not item_list:
            tree = es5(script)
            script_data = ast_to_dict(tree)
            try:
                item_list = script_data["window._dida_config_._init_data_"][
                    "data"]["data"]["root"]["fields"]["mods"]["itemList"]["content"]
            except KeyError:
                msg = "Failed to parse javascript with calmjs methods"
                await self.add_message(msg)
                return 'error'

        for item in item_list:
            try:
                product_id: int = int(self._get_nested_dict_item(item, "productId"))
                products[product_id] = {
                    "product_id": product_id,
                    "link": f"https://www.aliexpress.com/item/{product_id}.html",
                    "image": self._get_nested_dict_item(item, "image", "imgUrl"),
                    "title": self._get_nested_dict_item(item, "title", "displayTitle"),
                    "currency": self._get_nested_dict_item(item, "prices", "currencySymbol"),
                    "original_price": self._get_nested_dict_item(
                        item, "prices", "originalPrice", "minPrice"
                    ),
                    "sale_price": self._get_nested_dict_item(item, "prices", "salePrice", "minPrice"),
                    "shipping": self._get_nested_dict_item(
                        item, "sellingPoints", 0, "tagContent", "tagText"
                    ),
                    "store_title": self._get_nested_dict_item(item, "store", "storeName"),
                    "store_id": self._get_nested_dict_item(item, "store", "storeId"),
                    "store_link": f"https:{self._get_nested_dict_item(item, 'store', 'storeUrl')}",
                }
            except KeyError as e:
                msg = f"Can't find key {e} in JSON"
                await self.add_message(msg)
                return 'error'
            except ValueError as e:
                msg = f"Can't convert into int {e} in JSON"
                # Save error item to file
                with open('.errors.txt', 'a') as file:
                    # noinspection PyTypeChecker
                    json.dump(item, file, ensure_ascii=False, indent=4)
                await self.add_message(msg)
                return 'error'
        return products

    async def _parse_global_search_page(self, search: str, page: int = None, ) -> dict | str:
        """
        The function parses the page with the global search results and returns a dictionary with products,
        the number of the next page and the total number of pages in the search results
        {
            'item_list': {
                'product_id': {
                    'title': title,
                    ...
                },
            },
            'next_page': next_page,
            'page_count':page_count,
        }
        :param search:
        :param page:
        :return:
        """

        html = await self._get_html(search, page)
        if html == 'error':
            msg = "Failed to get HTML"
            await self.add_message(msg)
            return 'error'
        soup = BeautifulSoup(html, features="lxml")
        try:
            script = soup.find("script",
                               string=re.compile("window._dida_config_ =")
                               ).text
            # save_script(soup=soup, script_file= 'script.js')
        except AttributeError:
            msg = "Failed to get JavaScript"
            await self.add_message(msg)
            return 'error'
        products = {}
        if script:
            products = await self._get_script_items(script)
        if products == 'error':
            return 'error'

        next_page = await self._get_next_page_number(soup)
        page_count = await self._get_page_count(soup)

        if next_page == 'error' or page_count == 'error':
            return 'error'

        # filter product names for relevance to the request
        if self.filter_result:
            start_len = len(products)
            filtered_products = dict(filter(
                lambda p: self._is_relevant(p[1]['title'], search=search),
                products.items()))
            products = filtered_products
            msg = f"Filtered {len(products)} from {start_len} products"
            await self.add_message(msg)

        sorted_products = dict(sorted(products.items(),
                                      key=lambda item: item[1]['sale_price']))
        products = sorted_products

        return {'products': products,
                'next_page': next_page,
                'page_count': page_count,
                }

    async def _collect_product_stores(self, search: str) -> dict | str:
        """
        Returns a dictionary with the results of a global search for a single query,
        where the key is a link to a store and the value is a dictionary with products
        {
            store_link: {
                product_id: {
                    title:  'product_title',
                    ...
                },
            },
        }
        :param search:
        :return:
        """

        products = {}
        next_page = 1
        retry = 5
        zero_pages_count = 0
        while next_page:

            if next_page > self.max_page:
                msg = f'The maximum number of pages "{self.max_page}" in search results for "{search}" has been reached. Exit'
                await self.add_message(msg)
                break
            if zero_pages_count == self.max_zero_pages:
                msg = f"{zero_pages_count} pages with fully filtered products. Exit"
                await self.add_message(msg)
                break

            if await self.check_stop_flag():
                # msg = "Stop command received. Exit"
                # await self._add_message(msg)
                break
            page_data = await self._parse_global_search_page(search=search, page=next_page)

            while page_data == 'error' and retry:
                await self.pause()
                page_data = await self._parse_global_search_page(search=search, page=next_page)
                retry -= 1

            if page_data == 'error':
                msg = "Failed to get page data"
                await self.add_message(msg)
                return 'error'

            for product_id, product in page_data['products'].items():
                if product_id not in products:
                    products[product_id] = product

            page_count = page_data.get('page_count', None)
            msg = f'Processed {next_page}/{page_count} pages'
            await self.add_message(msg)
            next_page = page_data.get('next_page', None)

            if len(page_data['products']) == 0:
                zero_pages_count += 1

            await self.pause()

        stores = {}
        for product_id, product in products.items():
            store_link = product.get('store_link')
            if store_link in stores:
                stores[store_link].update({product_id: product})
            else:
                stores[store_link] = {product_id: product}

        msg = f'Total stores for request "{search}": {len(stores)}'
        await self.add_message(msg)
        msg = f'Total products for request "{search}": {len(products)}'
        await self.add_message(msg)

        return stores

    async def pause(self):
        if self.enable_pause:
            pause = random.randint(0, self.max_pause_time)
            msg = f"Pause for {pause} second"
            await self.add_message(msg)
            await asyncio.sleep(pause)

    async def intersection_in_global_search(self, queries_list: list):
        """
        The function searches for products in the global search in turn.
        Returns a dictionary with stores that were found by different queries, where the keys are a link to the store,
        and the values are a dictionary with products
        {
            store_link: {
                product_id: {
                    title:  'product_title',
                    ...
                },
            },
        }

        :param queries_list:
        :return:
        """
        # self.is_running = True
        msg = "Start searching"
        await self.add_message(msg)

        result_dict = {}
        all_stores: list[dict] = []
        for search_list in queries_list:
            one_product_stores: dict = {}
            for search in search_list:
                if await self.check_stop_flag():
                    # self.is_running = False
                    msg = "Stop command received"
                    await self.add_message(msg)
                    return None
                temp_stores = await self._collect_product_stores(search=search)
                if temp_stores == 'error':
                    msg = 'Failed to parse page'
                    await self.add_message(msg)
                    break
                # Results for different queries for one product save to one dictionary
                for store, products in temp_stores.items():
                    if store in one_product_stores:
                        one_product_stores[store] = one_product_stores[store] | products
                    else:
                        one_product_stores[store] = products
                await self.pause()
            # Save results for one product
            msg = f'Total stores by requests "{" and ".join(search_list)}" - {len(one_product_stores)}'
            await self.add_message(msg)
            if self.enable_save_to_json:
                report_name = f'{"_&_".join([search.replace(" ", "_") for search in search_list])}'
                self._save_report_as_json(one_product_stores, report_name)

            all_stores.append(one_product_stores)

        # Get intersection of stores in results
        # intersection_stores = set.intersection(*map(set, (d.keys() for d in all_stores)))
        intersection_stores = set.intersection(*(map(lambda d: set(d.keys()), all_stores)))

        for store in intersection_stores:
            result_dict[store]: dict = {}
            for one_product_stores in all_stores:
                if store in one_product_stores:
                    result_dict[store].update(one_product_stores[store])

        if self.enable_save_to_json:
            # Save results to JSON file
            report_name = f'results_{"_&_".join(["+".join([search.replace(" ", "_") for search in search_list]) for search_list in queries_list])}'
            self._save_report_as_json(data=result_dict, report_name=report_name)
        msg = f'Total stores by requests "{" and ".join(["+".join(i) for i in queries_list])}" - {len(result_dict)}'
        await self.add_message(msg)
        msg = 'Search finished'
        await self.add_message(msg)
        # self.is_running = False
        await self.save_search_results_to_redis(result_dict)
        return result_dict

    async def save_search_results_to_redis(self, results: dict):
        """
        Save search result into Redis
        :param results:
        :return:
        """

        serialized_results = {
            key: json.dumps(value) if isinstance(value, (dict, list)) else value
            for key, value in results.items()
        }

        sanitized_results = {
            key: ("" if value is None else str(value) if not isinstance(value, (str, bytes, int, float)) else value)
            for key, value in serialized_results.items()
        }

        await self.redis.hset(f"{self.session_id}:{self.search_uuid}:results", mapping=sanitized_results)
