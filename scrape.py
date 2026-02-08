import os
from datetime import UTC, datetime
from pathlib import Path

import bs4
import questionary
import typed_argparse as tap
from tqdm import tqdm
import curl_cffi

from classes import Args, Thread
from db import dump_threads, get_threads
from utility import get_thread_by_url

ACK = "404 - Not found"
BASE = "https://www.soyjak.st"

def process(path: Path, file) -> tuple[str, Path]:
    # Find the href attribute of the child element
    href: str = file.find("a", href=True).get("href")

    name: str = os.path.basename(href).split(".")[-1]

    location = Path(
        path
        / f"{name[0]} ({file.find('span', attrs={'class': 'filehash'}).getText()}).{name[-1]}"
    )
    return href, location


def info(
    path: Path, filelist: bs4.ResultSet[bs4.element.PageElement | bs4.Tag]
) -> tuple[int, int, list[bs4.element.PageElement]]:
    existing: int = 0
    duplicates: int = 0
    files: list[bs4.element.PageElement] = []
    locations: list[Path] = []

    # Dupe check
    for file in filelist:
        _, location = process(path, file)

        if location in locations:
            duplicates += 1
        elif os.path.exists(location):
            existing += 1
        else:
            locations.append(location)
            files.append(file)

    return existing, duplicates, files


def download(thread: Thread, unattended: bool) -> Thread:
    url = thread.url
    assert url.path

    board = url.path.split("/")[1]
    id = url.path.split("/")[3].split(".")[0]
    path: Path = Path(f"./out/[{board}] ({id})/")
    contents = bs4.BeautifulSoup(curl_cffi.get(str(url), impersonate="chrome").text, "html.parser")

    assert contents.title

    if contents.title.string == ACK:
        print(f"Thread #{id} on board '{board}' has -acked")
        if unattended:
            thread.acked = True
            return thread
        if questionary.confirm("Do you want to move it to locked?").ask():
            thread.acked = True
            return thread

    filelist: bs4.ResultSet[bs4.element.PageElement | bs4.Tag] = contents(class_="fileinfo")

    existing, duplicates, files = info(path, filelist)
    file_count = len(files)

    print(f"Thread #{id} on board '{board}' has:")

    match file_count:
        case 0:
            print("    - no files to downloaded")
        case 1:
            print("    - 1 file to downloaded")
        case _:
            print(f"    - {file_count} files to downloaded")

    print(f"    - {duplicates} duplicates")
    print(f"    - {existing} existing files")

    if not unattended:
        if not questionary.confirm("Do you want to continue?").ask():
            return thread

    if not os.path.exists(path):
        os.makedirs(path)

    if file_count > 0:
        progress_bar = tqdm(total=len(files), desc="Downloading Images")

        # Download files
        for file in files:
            href, location = process(path, file)
            img_response = curl_cffi.get(BASE + href, impersonate="chrome")

            with open(location, "wb") as file:
                _ = file.write(img_response.content)

            _ = progress_bar.update()

        progress_bar.close()

    if not isinstance(thread.name, str):
        subject = contents.find(class_="subject")

        if subject:
            thread.name = subject.getText()

    if not isinstance(thread.first_scraped, datetime):
        thread.first_scraped = datetime.now(UTC)

    thread.last_scraped = datetime.now(UTC)

    print()

    return thread


def runner(args: Args) -> None:
    threads_process: list[Thread] = []
    threads_done: list[Thread] = []
    threads_existing: list[Thread] = get_threads()

    for url in args.url:
        if get_thread_by_url(url, threads_existing) is None:
            threads_process.append(Thread(url))
        else:
            thread: Thread = get_thread_by_url(url, threads_existing)
            threads_process.append(thread)
            threads_existing.remove(thread)

    if args.reload:
        threads_process += threads_existing

    for thread in threads_process:
        threads_done.append(download(thread, args.unattended))

    dump_threads(threads_done)


if __name__ == "__main__":
    tap.Parser(Args).bind(runner).run()
