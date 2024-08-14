from typing import List, Optional

from pydantic import BaseModel


class SearchPageData(BaseModel):
    list1: List[str]
    list2: List[str]
    messages_html: Optional[str] = None
    results_html: Optional[str] = None