#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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


tmp_dir = os.path.join(tempfile.gettempdir(), "convert_ebook")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def kindle_gen_bin():
    system_name = platform.system()
    if system_name == "Windows":
        return os.path.abspath("kindlegen/kindlegen.exe")
    elif system_name == "Linux":
        return os.path.abspath("kindlegen/kindlegen-linux")
    elif system_name == "Darwin":
        return os.path.abspath("kindlegen/kindlegen-macos")
    else:
        logger.error("Current OS is not supported.")


def run_bash(command):
    return subprocess.call(command, shell=True, stdout=subprocess.DEVNULL)


def file_copy(from_file, to_file):
    logger.info("Copying {} to {}".format(from_file, to_file))
    shutil.copy(from_file, to_file)


def isKF8(file):
    sect = Sectionizer(file)
    if sect.ident != b'BOOKMOBI' and sect.ident != b'TEXtREAd':
        return False

    mh = MobiHeader(sect, 0)
    return mh.isK8()


def unpack_as_azw3(filepath, output_dir):
    kindleunpack.print = lambda str: str
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
        logger.error("File doest not exist: {}".format(file))
        return False
    if not isKF8(file):
        logger.error("File is not in mobi8 format: {}".format(file))
        return False
    return True


def convert_kf8_to_epub(file_path, tmp):
    unpack_as_azw3(file_path, tmp)
    mobi8_dir = os.path.join(tmp, "mobi8")
    if not os.path.exists(mobi8_dir):
        logger.error("Extraction process failed: {}".format(file_path))
        return

    file = find_suffix(mobi8_dir, ".epub")
    if file and os.path.exists(file):
        logger.info("Epub file is successfully generated: {}".format(file))
    else:
        logger.error("Epub file cannot be generated.")
    return file


def convert_epub_to_mobi(file_path, tmp):
    exit_code = run_bash("%s -dont_append_source \"%s\"" % (kindle_gen_bin(), file_path))
    if exit_code != 0:
        return
    file = find_suffix(os.path.abspath(os.path.join(file_path, os.path.pardir)), ".mobi")
    if file and os.path.exists(file):
        logger.info("Mobi file is successfully generated: {}".format(file))
    else:
        logger.error("Mobi file cannot be generated.")
    return file


def convert_azw3_to_mobi(file_path, tmp):
    if not check_file(file_path):
        return

    temp_dir_name = str(uuid.uuid1())
    temp_dir = os.path.join(tmp, temp_dir_name)
    if os.path.exists(temp_dir):
        shutil.rmtree(tmp_dir)
    os.makedirs(temp_dir)

    logger.info("Converting to epub: {}".format(file_path))
    epub_file = convert_kf8_to_epub(file_path, temp_dir)

    is_azw3 = str(file_path).lower().endswith(".azw3")

    file_source_suffix = ".azw3" if is_azw3 else file_path[file_path.rfind("."):]

    if epub_file:
        file_copy(epub_file, file_path.replace(file_source_suffix, ".epub"))

    mobi_file = None
    if epub_file and is_azw3:
        logger.info("Converting to mobi: {}".format(epub_file))
        mobi_file = convert_epub_to_mobi(epub_file, temp_dir)

    if mobi_file:
        file_copy(mobi_file, file_path.replace(file_source_suffix, ".mobi"))


if __name__ == "__main__":
    if len(sys.argv) <= 1:
        logger.error("The argument is not provided.")
        exit(1)
    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        logger.error("File does not exist: {}".format(file_path))
        exit(1)
    file_ext = os.path.splitext(file_path)[-1]
    if file_ext == ".azw3":
        convert_azw3_to_mobi(file_path, tmp_dir)
    elif file_ext == ".epub":
        convert_epub_to_mobi(file_path, tmp_dir)
    else:
        logger.error("File extension is not supported: {}".format(file_ext))
