#!/usr/bin/env python3
import argparse
import os
import sys
from pathlib import Path
from time import time

import requests
from humanfriendly import format_timespan, format_size
from requests.auth import HTTPBasicAuth
from yaspin import yaspin
from yaspin.core import Yaspin  # only needed for type hinting
from yaspin.spinners import Spinners

spinner: Yaspin  # initialize sp as global terminal spinner


def main() -> None:
    args: argparse.Namespace = parse_args()
    auth: HTTPBasicAuth = HTTPBasicAuth(args.case, args.token)
    start_time: float = time()
    if args.file is None:
        if not args.dir.is_dir():
            print(f'{args.dir} is not a directory.')
            sys.exit(255)
        else:
            return_code: int = dir_upload(args.dir, auth, args.threads)
            if args.stats:
                print(
                    f'Uploaded {format_size(size := get_dir_size(args.dir), binary=True)} in {format_timespan(elapsed_time := time() - start_time)} at an average rate of {format_size(round(size / elapsed_time), binary=True)}/s'
                )
            sys.exit(None if return_code == 201 else return_code)
    else:
        if not args.file.is_file():
            print(f'{args.file} is not a file.')
            sys.exit(255)
        else:
            global spinner
            with yaspin(Spinners.material, text='Uploading --- Elapsed Time', color='green', timer=True) as spinner:
                return_code: int = file_upload(args.file, auth)
                if return_code == 201:
                    spinner.ok("✔ ")
                else:
                    spinner.fail("💥 ")
            sys.exit(None if return_code == 201 else return_code)


def parse_args() -> argparse.Namespace:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Upload files or directories to a TAC case via CXD",
        epilog="Case, token and either file or dir arguments are required")
    parser.add_argument('-s', '--stats', help='Print detailed stats upon exit', action='store_true')
    parser.add_argument('-p', '--threads', help='Number of threads', default=4, type=int, choices=range(1, 9))
    parser.add_argument('-c', '--case', required=True, help='Cisco TAC Case #')
    parser.add_argument('-t', '--token', required=True, help='CXD Token')
    file_dir = parser.add_mutually_exclusive_group(required=True)
    file_dir.add_argument('-f', '--file', help='A single file to attach', type=lambda p: Path(p).absolute())
    file_dir.add_argument('-d', '--dir', help='Directory to attach', type=lambda p: Path(p).absolute())
    # noinspection SpellCheckingInspection
    parser.add_argument('--version', action='version', version='%(prog)s version 1.1')
    return parser.parse_args()


def file_upload(send_file: str, auth: HTTPBasicAuth) -> int:
    base_url: str = 'https://cxd.cisco.com/home/'
    global spinner
    spinner.write(f'Executing file upload of {(base_send_file := os.path.basename(send_file))}')
    with open(send_file, 'rb') as open_file:
        try:
            response: requests.Response = requests.put(base_url + base_send_file, open_file, auth=auth, timeout=120)
        except requests.ConnectTimeout:
            spinner.write(f'Upload thread connect timeout {base_send_file}')
            spinner.color = 'red'
            return 1000
        except IOError as e:
            spinner.write(f'IOError: {base_send_file} - {e}')
            spinner.color = 'red'
            return 1001
        except requests.exceptions as e:
            spinner.write(f'Upload thread failed {base_send_file} - {e}')
            spinner.color = 'red'
            return 1002
    if response.status_code == 201:
        spinner.write(f'{base_send_file} uploaded successfully')
        if spinner.color == 'red':
            spinner.color = 'yellow'
    elif response.status_code == 401:
        spinner.write('Failed authentication please verify your case # and token')
        spinner.color = 'red'
    else:
        spinner.write(f'{base_send_file} failed with response code {response.status_code}')
        spinner.color = 'red'
    return response.status_code


def dir_upload(send_dir: str, auth: HTTPBasicAuth, threads: int) -> int:
    import concurrent.futures as cf
    global spinner
    with yaspin(Spinners.material, text='Uploading', color='green', timer=True) as spinner:
        with cf.ThreadPoolExecutor(max_workers=threads, thread_name_prefix='cxd_put') as executor:
            futures: list[cf.Future] = []
            spinner.text = f'Completed {(files_complete := 0)} of {(total_files := len(os.listdir(send_dir)))} files - Elapsed Time'
            with os.scandir(send_dir) as files:
                for file in files:
                    if file.is_file():
                        futures.append(executor.submit(file_upload, file.path, auth))
            for future in cf.as_completed(futures):
                if future.result() == 201:
                    files_complete += 1
                    spinner.text = f'Completed {files_complete} of {total_files} files - Elapsed Time'
        if files_complete == total_files:
            spinner.ok("✔ ")
            return 201
        else:
            spinner.fail("💥 ")
            return 1000


def get_dir_size(path: str) -> int:
    dir_size: int = 0
    with os.scandir(path) as files:
        for file in files:
            if file.is_file():
                dir_size += file.stat().st_size
    #       elif file.is_dir():
    #           dir_size += get_dir_size(file.path)
    return dir_size


if __name__ == '__main__':
    main()
