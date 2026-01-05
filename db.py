from pathlib import Path
from typing import Any

import rtoml

from classes import Thread
from utility import get_thread_by_url


def get_threads() -> list[Thread]:
    return [
        Thread.from_dict(thread)
        for thread in rtoml.load(Path("./threads.toml"))["keyed"]
    ]


def dump_threads(new_threads: list[Thread]) -> None:
    data = rtoml.load(Path("./threads.toml"))
    threads: list[Thread] = []
    result: dict[str, list[dict[str, Any]]] = {"keyed": [], "locked": []}

    if "keyed" in data:
        threads.extend(
            [Thread.from_dict(thread, acked=False) for thread in data["keyed"]]
        )

    if "locked" in data:
        threads.extend(
            [Thread.from_dict(thread, acked=True) for thread in data["locked"]]
        )

    for thread in new_threads:
        try:
            threads.remove(get_thread_by_url(thread.url, threads))
        except ValueError:
            pass
        threads.append(thread)

    for thread in threads:
        if thread.acked:
            result["locked"].append(thread.to_dict())
        else:
            result["keyed"].append(thread.to_dict())

    _ = rtoml.dump(
        {key: value for key, value in result.items() if value not in [[]]},
        Path("./threads.toml"),
    )
