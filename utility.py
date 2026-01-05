import os

from pydantic_core import Url

from classes import Thread


def convert() -> dict[str, list[Thread]]:
    data: dict[str, list[Thread]] = {"keyed": []}

    for folder in os.listdir("./out"):
        data["keyed"].append(
            Thread(
                Url(
                    f"https://www.soyjak.st/{folder.split()[0][1:-1]}/thread/{folder.split()[1][1:-1]}.html"
                ),
            )
        )

    return data


def get_thread_by_url(url: Url, thread_list: list[Thread]) -> Thread | None:
    for thread in thread_list:
        if thread.url == url:
            return thread
    return None
