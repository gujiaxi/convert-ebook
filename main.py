#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import contextlib
import io
import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from KindleUnpack.lib import kindleunpack
from KindleUnpack.lib.mobi_header import MobiHeader
from KindleUnpack.lib.mobi_sectioner import Sectionizer


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


if getattr(sys, "frozen", False):
    # we are running in a bundle
    bundle_dir = sys._MEIPASS
else:
    # we are running in a normal Python environment
    bundle_dir = os.path.dirname(os.path.abspath(__file__))


KINDLEGEN_BY_SYSTEM = {
    "Windows": "kindlegen.exe",
    "Linux": "kindlegen-linux",
    "Darwin": "kindlegen-macos",
}


def kindle_gen_bin():
    """Return the kindlegen binary path for the current OS, or None."""
    system_name = platform.system()
    binary_name = KINDLEGEN_BY_SYSTEM.get(system_name)
    if binary_name is None:
        logger.error(f"Current OS is not supported: {system_name}")
        return None

    binary_path = Path(bundle_dir, "kindlegen", binary_name).resolve()
    if not binary_path.exists():
        logger.error(f"kindlegen binary is missing: {binary_path}")
        return None
    if not os.access(binary_path, os.X_OK):
        logger.error(f"kindlegen binary is not executable: {binary_path}")
        return None
    return str(binary_path)


def run_bin(args):
    """Run an external binary without a shell to avoid injection."""
    logger.debug("Running: %s", args)
    return subprocess.call(args, stdout=subprocess.DEVNULL)


def file_copy(from_file, to_file):
    logger.info(f"Copying {from_file} to {to_file}")
    shutil.copy(from_file, to_file)


def is_kf8(file):
    """Return True when the file is a KF8 (mobi8) container."""
    try:
        sect = Sectionizer(file)
        if sect.ident not in (b"BOOKMOBI", b"TEXtREAd"):
            return False
        return MobiHeader(sect, 0).isK8()
    except Exception as exc:
        logger.error(f"Cannot parse ebook header: {file} ({exc})")
        return False


def unpack_as_azw3(filepath, output_dir, verbose=False):
    """Unpack a KF8 file into output_dir, silencing KindleUnpack by default."""
    argv = ["-i", "-s", "--epub_version=3", filepath, output_dir]
    if verbose:
        kindleunpack.main(argv)
        return
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        kindleunpack.main(argv)
    logger.debug("KindleUnpack output:\n%s", buffer.getvalue())


def find_suffix(directory, suffix):
    """Recursively find the first file matching suffix, sorted for stability."""
    matches = sorted(
        path for path in Path(directory).rglob("*")
        if path.is_file() and path.suffix.lower() == suffix.lower()
    )
    return str(matches[0]) if matches else None


def check_file(file):
    if not os.path.exists(file):
        logger.error(f"File does not exist: {file}")
        return False
    if not is_kf8(file):
        logger.error(f"File is not in mobi8 format: {file}")
        return False
    return True


def convert_kf8_to_epub(file_path, output_dir, verbose=False):
    unpack_as_azw3(file_path, output_dir, verbose=verbose)
    mobi8_dir = os.path.join(output_dir, "mobi8")
    if not os.path.exists(mobi8_dir):
        logger.error(f"Extraction process failed: {file_path}")
        return None
    epub_file = find_suffix(mobi8_dir, ".epub")
    if epub_file:
        logger.info("Epub file is successfully generated.")
    else:
        logger.error("Epub file cannot be generated.")
    return epub_file


def convert_epub_to_mobi(file_path):
    binary_path = kindle_gen_bin()
    if binary_path is None:
        return None

    exit_code = run_bin([binary_path, "-dont_append_source", str(file_path)])
    if exit_code != 0:
        logger.error(f"kindlegen exited with code {exit_code}: {file_path}")
        return None

    parent_dir = Path(file_path).resolve().parent
    mobi_file = find_suffix(parent_dir, ".mobi")
    if mobi_file:
        logger.info("Mobi file is successfully generated.")
    else:
        logger.error("Mobi file cannot be generated.")
    return mobi_file


def convert_azw3(file_path, force_to_mobi=False, verbose=False):
    """Convert an AZW3/KF8 file to epub, optionally to mobi as well.

    Returns True only when every requested output was produced.
    """
    if not check_file(file_path):
        return False

    source = Path(file_path)
    with tempfile.TemporaryDirectory(prefix="convert_ebook_") as tmp_dir:
        logger.info(f"Converting to epub: {file_path}")
        epub_file = convert_kf8_to_epub(file_path, tmp_dir, verbose=verbose)
        if not epub_file:
            return False

        epub_target = source.with_suffix(".epub")
        file_copy(epub_file, epub_target)

        if not force_to_mobi:
            return True

        logger.info(f"Converting to mobi: {epub_target}")
        mobi_file = convert_epub_to_mobi(epub_target)
        if not mobi_file:
            return False

        mobi_target = source.with_suffix(".mobi")
        if Path(mobi_file).resolve() != mobi_target.resolve():
            file_copy(mobi_file, mobi_target)
        return True


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert Kindle ebooks: azw3 -> epub (-> mobi), or epub -> mobi."
    )
    parser.add_argument(
        "file_path", type=str, help="Local ebook file (.azw3/.epub)."
    )
    parser.add_argument(
        "--force_to_mobi", action="store_true",
        help="Convert AZW3 to epub, then to mobi.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Show KindleUnpack output for troubleshooting.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    if not os.path.exists(args.file_path):
        logger.error(f"File not found: {args.file_path}")
        return 1

    file_ext = Path(args.file_path).suffix.lower()
    if file_ext == ".azw3":
        succeeded = convert_azw3(
            args.file_path,
            force_to_mobi=args.force_to_mobi,
            verbose=args.verbose,
        )
    elif file_ext == ".epub":
        succeeded = convert_epub_to_mobi(args.file_path) is not None
    else:
        logger.error(f"File extension is not supported: {file_ext}")
        return 1

    if not succeeded:
        logger.error(f"Conversion failed: {args.file_path}")
        return 1

    logger.info("Ebook is successfully converted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
