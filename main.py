import csv
import re
import sqlite3
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Tag

from AnnounceRecord import AnnounceRecord

LIMIT = 2

def select(
    url: str, selector: str, single: bool = False, text: bool = False
) -> list[Tag] | Tag | None:
    response = requests.get(url)
    response.encoding = "utf-8"
    html_content = response.text
    soup = BeautifulSoup(html_content, "html.parser")
    if single and not text:
        return soup.select_one(selector)
    elif single and text:
        return soup.find(string=re.compile(selector))
    elif not single and not text:
        return list(soup.select(selector))
    elif not single and text:
        return list(soup.find_all(string=re.compile(selector)))
    return [] # unreachable


# 截止日期和联系人需要从正文中抓取
def scrape_page(url: str, year: int) -> tuple[datetime | None, str]:
    selection = select(url, ".xwnr_content", single=True)
    texts: str = selection.get_text() if selection else ""
    due_capture = re.search(r"截止(?:(?:日期)|(?:时间))：(.+?日)", texts)
    due_date = None
    if due_capture:
        try:
            due_date = datetime.strptime(due_capture.group(1), "%Y年%m月%d日")
        except ValueError:
            try:
                due_date = datetime.strptime(due_capture.group(1), "%m月%d日").replace(year=year)
            except ValueError:
                pass

    contact = select(url, "联系人：", single=True, text=True)
    if contact:
        contact = contact.get_text(strip=True)
        contact = re.sub(r"^.*联系人：", "", contact)
        contact = re.sub(r"(?<=老师).*$", "", contact)
        contact = re.sub(r"；.+$", "", contact)
    else:
        contact = ""
    return due_date, contact


def scrape_list(urls: list[str]) -> list[list[str]]:
    output_rows = [
        ["项目名称", "项目类型", "发布日期", "截止日期", "联系人", "网页URL"]
    ]
    for url in urls:
        selection = select(url, ".xw-list ul li a")
        items = selection if selection else []
        for item in items:
            if len(output_rows) >= LIMIT:
                break
            # obj = AnnounceRecord()
            post_date = item.find_next_sibling("span").get_text(strip=True)[1:11]
            post_date = datetime.strptime(post_date, "%Y.%m.%d")
            href = item["href"]
            base_url = "https://www.dufe.edu.cn/"
            url = base_url + href.lstrip("/")

            title = item.get_text(strip=True)
            print(f"Scraping {len(output_rows)}:{title}")
            exclude_keywords = ["研讨会", "实践"]
            if any(keyword in title for keyword in exclude_keywords):
                continue
            # TODO: 类型怎么获取？
            type_mapping = {
                re.compile(r"(申报)"): "课题申报",
                re.compile(r"(结题)"): "项目结题",
                re.compile(r"(认定)"): "成果认定",
                re.compile(r"(评级)"): "成果评级",
            }
            for pattern, _type in type_mapping.items():
                if pattern.search(title):
                    type = _type
                    break
            else:
                type = "其他"
            remove_phrases = ["关于组织", "关于", "工作的通知", "的通知"]
            for phrase in remove_phrases:
                title = title.replace(phrase, "")
            title = title.strip()
            due_date, contact = scrape_page(url, post_date.year)
            obj = AnnounceRecord(
                name=title,
                type=type,
                post_date=post_date,
                due_date=due_date,
                contact=contact,
                url=url,
            )
            output_rows.append(obj.to_csv_row())
    return output_rows


def to_csv(data: list[list[str]]) -> None:
    with open("output.csv", mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerows(data)
    print("CSV 文件已写入！")


def to_db(data: list[list[str]]) -> None:
    headers = data[0]
    rows = data[1:]
    if Path("output.db").exists():
        Path("output.db").unlink()
    conn = sqlite3.connect("output.db")
    cursor = conn.cursor()
    table_name = "announces"
    # 创建表
    columns_def = ", ".join([f'"{col}" TEXT' for col in headers])
    cursor.execute(f'DROP TABLE IF EXISTS "{table_name}"')
    cursor.execute(f'CREATE TABLE "{table_name}" ({columns_def})')
    # 插入数据
    placeholders = ", ".join(["?"] * len(headers))
    cursor.executemany(f'INSERT INTO "{table_name}" VALUES ({placeholders})', rows)
    conn.commit()
    conn.close()
    print("数据已写入 SQLite 数据库表!")


if __name__ == "__main__":
    urls = [f"https://www.dufe.edu.cn/r_6_{i}.html" for i in range(1, 4)]  # 3 页
    output_rows = scrape_list(urls)
    # print(output_rows)
    to_csv(output_rows)
    to_db(output_rows)
