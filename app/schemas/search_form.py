from typing import Optional, Any
from pydantic import BaseModel, ConfigDict


class SearchForm(BaseModel):
    model_config = ConfigDict(from_attributes=True,
                              str_strip_whitespace=True,
                              extra="ignore")
    search_uuid: Optional[str] = None
    list1: list[str]
    list2: list[str]

    @property
    def queries_list(self):
        return [tuple(self.list1), tuple(self.list2)]


class SearchFormSave(SearchForm):
    messages: Optional[list[str]] = None
    results: Optional[dict[str, Any]] = None
