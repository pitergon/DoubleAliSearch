from typing import Optional, Any
from pydantic import BaseModel, ConfigDict


class SearchForm(BaseModel):
    model_config = ConfigDict(from_attributes=True,
                              str_strip_whitespace=True,
                              extra="ignore")
    names_list1: list[str]
    names_list2: list[str]

    @property
    def queries_list(self):
        return [tuple(self.names_list1), tuple(self.names_list2)]


class SearchFormSave(SearchForm):
    # search_uuid: Optional[str] = None
    messages: Optional[list[str]] = None
    results: Optional[dict[str, Any]] = None
