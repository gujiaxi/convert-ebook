#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import uuid

from KindleUnpack.lib import kindleunpack
from KindleUnpack.lib.mobi_header import MobiHeader
from KindleUnpack.lib.mobi_sectioner import Sectionizer


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


if getattr(sys, 'frozen', False):
    # we are running in a bundle
    bundle_dir = sys._MEIPASS
else:
    # we are running in a normal Python environment
    bundle_dir = os.path.dirname(os.path.abspath(__file__))


def kindle_gen_bin():
    system_name = platform.system()
    if system_name == "Windows":
        return os.path.abspath(os.path.join(bundle_dir, "kindlegen/kindlegen.exe"))
    elif system_name == "Linux":
        return os.path.abspath(os.path.join(bundle_dir, "kindlegen/kindlegen-linux"))
    elif system_name == "Darwin":
        return os.path.abspath(os.path.join(bundle_dir, "kindlegen/kindlegen-macos"))
    else:
        logger.error("Current OS is not supported.")


def run_bash(command):
    return subprocess.call(command, shell=True, stdout=subprocess.DEVNULL)


def file_copy(from_file, to_file):
    logger.info(f"Copying {from_file} to {to_file}")
    shutil.copy(from_file, to_file)


def isKF8(file):
    sect = Sectionizer(file)
    if sect.ident != b'BOOKMOBI' and sect.ident != b'TEXtREAd':
        return False

    mh = MobiHeader(sect, 0)
    return mh.isK8()


def unpack_as_azw3(filepath, output_dir):
    kindleunpack.print = lambda x, *args: x
    kindleunpack.main(["-i", "-s", "--epub_version=3", filepath, output_dir])


def find_suffix(dir, suffix):
    for name in os.listdir(dir):
        path_join = os.path.join(dir, name)
        if os.path.isdir(path_join):
            find_suffix(path_join, suffix)
        elif name.endswith(suffix):
            return path_join


def check_file(file):
    if not os.path.exists(file):
        logger.error(f"File doest not exist: {file}")
        return False
    if not isKF8(file):
        logger.error(f"File is not in mobi8 format: {file}")
        return False
    return True


def convert_kf8_to_epub(file_path, output_dir):
    unpack_as_azw3(file_path, output_dir)
    mobi8_dir = os.path.join(output_dir, "mobi8")
    if not os.path.exists(mobi8_dir):
        logger.error(f"Extraction process failed: {file_path}")
        return
    file = find_suffix(mobi8_dir, ".epub")
    if file and os.path.exists(file):
        logger.info("Epub file is successfully generated.")
    else:
        logger.error("Epub file cannot be generated.")
    return file


def convert_epub_to_mobi(file_path):
    exit_code = run_bash("%s -dont_append_source \"%s\"" % (kindle_gen_bin(), file_path))
    if exit_code != 0:
        return
    file = find_suffix(os.path.abspath(os.path.join(file_path, os.path.pardir)), ".mobi")
    if file and os.path.exists(file):
        logger.info("Mobi file is successfully generated.")
    else:
        logger.error("Mobi file cannot be generated.")
    return file


def convert_azw3_to_mobi(file_path, force_to_mobi=False):
    if not check_file(file_path):
        return

    tmp_dir = os.path.join(tempfile.gettempdir(), f"convert_ebook_{uuid.uuid4().hex}")
    os.makedirs(tmp_dir)

    logger.info(f"Converting to epub: {file_path}")
    epub_file = convert_kf8_to_epub(file_path, tmp_dir)

    is_azw3 = str(file_path).lower().endswith(".azw3")

    file_source_suffix = ".azw3" if is_azw3 else file_path[file_path.rfind("."):]

    if epub_file:
        file_copy(epub_file, file_path.replace(file_source_suffix, ".epub"))

    mobi_file = None
    if force_to_mobi and epub_file and is_azw3:
        logger.info(f"Converting to mobi: {epub_file}")
        mobi_file = convert_epub_to_mobi(epub_file)
    if mobi_file:
        file_copy(mobi_file, file_path.replace(file_source_suffix, ".mobi"))
    # cleanup
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "file_path", type=str, help="Local ebook file (.azw3/.epub)."
    )
    parser.add_argument(
        "--force_to_mobi", action="store_true", help="Convert AZW3 to epub, then to mobi."
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if not os.path.exists(args.file_path):
        logger.error(f"File not found: {args.file_path}")
        exit(1)
    file_ext = os.path.splitext(args.file_path)[-1]
    if file_ext == ".azw3":
        convert_azw3_to_mobi(args.file_path, force_to_mobi=args.force_to_mobi)
    elif file_ext == ".epub":
        convert_epub_to_mobi(args.file_path)
    else:
        logger.error(f"File extension is not supported: {file_ext}")
    logger.info("Ebook is successfully converted.")
