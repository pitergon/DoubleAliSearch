from typing import Optional, Any
from pydantic import BaseModel


class SearchPageData(BaseModel):
    list1: list[str]
    list2: list[str]
    messages: Optional[list[str]] = None
    results: Optional[dict[str, Any]] = None


    @property
    def queries_list(self):
        return [tuple(self.list1), tuple(self.list2)]