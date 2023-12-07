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
from yaspin.core import Yaspin   # only needed for type hinting
from yaspin.spinners import Spinners

sp: Yaspin  # initialize sp as global terminal spinner


def main() -> None:
    args: argparse.Namespace = parse_args()
    auth: HTTPBasicAuth = HTTPBasicAuth(args.case, args.token)
    start_time: float = time()
    if args.file is None:
        if not args.dir.is_dir():
            print(f'{args.dir} is not a directory.')
            sys.exit(255)
        else:
            dir_upload(args.dir, auth, args.threads)
            if args.stats:
                print_stats(get_dir_size(args.dir), start_time)
                sys.exit()
            else:
                print(f'Upload time: {format_timespan(time() - start_time)}')
                sys.exit()
    else:
        if not args.file.is_file():
            print(f'{args.file} is not a file.')
            sys.exit(255)
        else:
            global sp
            with yaspin(Spinners.material, text='Uploading --- Elapsed Time', color='green', timer=True) as sp:
                return_code: int = file_upload(args.file, auth)
                if return_code == 201:
                    sp.ok("✔ ")
                else:
                    sp.fail("💥 ")
            print(f'Upload time: {format_timespan(time() - start_time)}')
            sys.exit(return_code)


def parse_args() -> argparse.Namespace:
    msg: str = "Upload files or directories to a TAC case via CXD"
    epi: str = "Case, token and either file or dir arguments are required"
    parser = argparse.ArgumentParser(description=msg, epilog=epi)
    parser.add_argument('-s', '--stats', help='Print detailed stats upon exit', action='store_true')
    parser.add_argument('-p', '--threads', help='Number of threads', default=4, type=int,
                        choices=range(1, 9))
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
    global sp
    sp.write(f'Executing file upload of {(base_send_file := os.path.basename(send_file))}')
    with open(send_file, 'rb') as open_file:
        try:
            response = requests.put(base_url + base_send_file, open_file, auth=auth, timeout=120)
        except requests.ConnectTimeout:
            sp.write(f'Upload thread connect timeout {base_send_file}')
            sp.color = 'red'
            return 1000
        except IOError as exception:
            sp.write(f'IOError: {base_send_file} - {exception}')
            sp.color = 'red'
            return 1001
        except requests.exceptions as exception:
            sp.write(f'Upload thread failed {base_send_file} - {exception}')
            sp.color = 'red'
            return 1002
    if response.status_code == 201:
        sp.write(f'{base_send_file} uploaded successfully')
        if sp.color == 'red':
            sp.color = 'yellow'
    elif response.status_code == 401:
        sp.write('Failed authentication please verify your case # and token')
        sp.color = 'red'
    else:
        sp.write(f'{base_send_file} failed with response code {response.status_code}')
        sp.color = 'red'
    return response.status_code


def dir_upload(send_dir: str, auth: HTTPBasicAuth, threads: int) -> None:
    import concurrent.futures as cf
    global sp
    with yaspin(Spinners.material, text='Uploading', color='green', timer=True) as sp:
        with cf.ThreadPoolExecutor(max_workers=threads, thread_name_prefix='cxd_put') as executor:
            futures: list[cf.Future] = []
            sp.text = f'Completed {(files_complete := 0)} of {(total_files := len(os.listdir(send_dir)))} files - Elapsed Time'
            with os.scandir(send_dir) as files:
                for file in files:
                    if file.is_file():
                        futures.append(
                            executor.submit(file_upload, file.path, auth))
            for future in cf.as_completed(futures):
                if future.result() == 201:
                    files_complete += 1
                    sp.text = f'Completed {files_complete} of {total_files} files - Elapsed Time'
        if files_complete == total_files:
            sp.ok("✔ ")
        else:
            sp.fail("💥 ")
    return


def get_dir_size(path: str) -> int:
    dir_size: int = 0
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                dir_size += entry.stat().st_size
    #            elif entry.is_dir():
    #               dir_size += get_dir_size(entry.path)
    return dir_size


def print_stats(size: int, start_time: float) -> None:
    elapsed_time: float = time() - start_time
    print(
        f'Uploaded {format_size(size, binary=True)} in {format_timespan(elapsed_time)} at an average rate of {format_size(round(size / elapsed_time), binary=True)}/s')
    return


if __name__ == '__main__':
    main()
