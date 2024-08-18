import asyncio
import json
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.staticfiles import StaticFiles

from .models.search_model import SearchPageData

from .search_engine import SearchEngine

import psycopg2
from psycopg2.extras import DictCursor

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class SearchApp:
    def __init__(self):

        self.app = FastAPI()

        # static files
        self.static_directory = os.path.join(BASE_DIR, 'static')
        self.app.mount("/static", StaticFiles(directory=self.static_directory), name="static")

        # include templates
        self.templates_directory = os.path.join(BASE_DIR, 'templates')
        self.templates = Jinja2Templates(directory=self.templates_directory)

        self.messages_lock = asyncio.Lock()
        self.results_lock = asyncio.Lock()
        self.read_messages = []
        self.results = {}
        self.is_running = False
        self.background_tasks = set()
        self.se = SearchEngine(messages_lock=self.messages_lock)

        # Define routes
        self.app.get("/", response_class=HTMLResponse)(self.index_endpoint)
        self.app.post("/start_search")(self.start_search_endpoint)
        self.app.post("/stop_search")(self.stop_search_endpoint)
        self.app.get("/get_messages")(self.get_messages_endpoint)
        self.app.get("/search/{search_id}")(self.search_id_endpoint)
        self.app.get("/history")(self.history_endpoint)
        self.app.post("/save_search")(self.save_search_endpoint)
        load_dotenv(os.path.join(BASE_DIR, '.env'))

    async def index_endpoint(self, request: Request):
        # "/"
        return self.templates.TemplateResponse("search.html", {"request": request})

    async def start_search_endpoint(self, page_data: SearchPageData):
        # "/start_search"
        if not page_data.list1 or not page_data.list2:
            return {"error": "Both lists must have at least one item."}
        if not self.is_running:
            await self._prepare_search()
            query_list: list[tuple] = [tuple(page_data.list1), tuple(page_data.list2)]
            await self._create_search_task(query_list)
        return {"messages": "Search started"}

    async def stop_search_endpoint(self):
        # "/stop_search"
        print("try to stop")
        self.is_running = False
        self.se.stop_flag = True
        self.read_messages.clear()
        self.background_tasks.clear()
        return {"status": "Search stopped by user"}

    async def get_messages_endpoint(self):
        # "/get_messages"
        msgs = await self._get_messages()
        response = {}
        response["messages"] = msgs
        if not self.is_running:
            response["search_finished"] = True
            async with self.results_lock:
                response["results"] = self.results
        return response

    async def search_id_endpoint(self, request: Request, search_id):
        # "/search/{search_id}"

        query = """
        SELECT  messages, results, names_list1, names_list2
        FROM history 
        WHERE search_id = %s
        """

        connection = self._create_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, (search_id,))
                result = cursor.fetchone()
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            print(f"Database error: {e}")
        finally:
            connection.close()

        if result:
            messages, results, names_list1, names_list2 = result
        else:
            messages = results = names_list1 = names_list2 = None

        return self.templates.TemplateResponse("search.html", {
            "request": request,
            "messages": json.dumps(messages),
            "results": json.dumps(results),
            "names_list1": names_list1,
            "names_list2": names_list2
        })

    async def save_search_endpoint(self, page_data: SearchPageData):
        if not page_data.list1 or not page_data.list2:
            return {"error": "Both lists must have at least one item."}
        postgres_insert_query = """
        INSERT INTO history (messages, results, names_list1, names_list2) 
        VALUES (%s,%s,%s,%s) 
        RETURNING search_id
        """
        values = (page_data.messages, json.dumps(page_data.results), page_data.list1, page_data.list2)
        connection = self._create_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(postgres_insert_query, values)
                last_inserted_id = cursor.fetchone()[0]
                connection.commit()
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            print(f"Database error: {e}")
        finally:
            connection.close()
        return {"messages": "Saved successfully",
                "url": f"/search/{last_inserted_id}",
                }

    async def history_endpoint(self, request: Request):
        query = """
        SELECT 
            search_id, 
            created_at, 
            names_list1, 
            names_list2,
            (SELECT COUNT(*) 
                FROM json_object_keys(results) AS keys) AS results_number
        FROM history
        ORDER BY created_at DESC;
        """

        connection = self._create_connection()
        try:
            with connection.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute(query)
                history = cursor.fetchall()
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            print(f"Database error: {e}")
        finally:
            connection.close()

        for record in history:
            record['created_at'] = record['created_at'].strftime('%Y-%m-%d %H:%M:%S')

        return self.templates.TemplateResponse("history.html", {
            "request": request,
            "history": history,
        })

    async def _prepare_search(self):
        self.is_running = True
        self.read_messages.clear()
        self.background_tasks.clear()
        self.se.stop_flag = False
        async with self.results_lock:
            self.results = {}
        async with self.messages_lock:
            self.se.messages.clear()

    async def _create_search_task(self, query_list: list[tuple]):
        search_task = asyncio.create_task(self._run_search(query_list))
        self.background_tasks.add(search_task)
        search_task.add_done_callback(self.background_tasks.discard)

    async def _run_search(self, query_list: list[tuple]):
        results = await self.se.intersection_in_global_search(query_list)
        async with self.results_lock:
            self.results = results
        self.is_running = False

    async def _get_messages(self):
        async with self.messages_lock:
            new_messages = self.se.messages[len(self.read_messages):]
        self.read_messages.extend(new_messages)
        return new_messages

    @staticmethod
    def _create_connection():
        return psycopg2.connect(
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT'),
            database=os.getenv('DB_DATABASE')
        )


search_app = SearchApp()
app = search_app.app
