from dataclasses import dataclass
from datetime import datetime

@dataclass
class AnnounceRecord:
    name: str
    type: str
    post_date: datetime
    due_date: datetime | None
    contact: str | None
    url: str

    def to_csv_row(self):
        return [
          self.name, 
          self.type, 
          self.post_date.strftime('%Y年%m月%d日'), 
          self.due_date.strftime('%Y年%m月%d日') if self.due_date else '', 
          self.contact, 
          self.url
        ]
