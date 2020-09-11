#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2019 Matt Post <post@cs.jhu.edu>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Used to add revisions to the Anthology.
Assumes all files have a base format like ANTHOLOGY_ROOT/P/P18/P18-1234.pdf format.
The revision process is as follows.

- The original paper is named as above.
- When a first revision is created, the original paper is archived to PYY-XXXXv1.pdf.
- The new revision is copied to PYY-XXXXvN, where N is the next revision ID (usually 2).
  The new revision is also copied to PYY-XXXX.pdf.
  This causes it to be returned by the anthology when the base paper format is queried.

Usage:

  add_revision.py [-e] paper_id URL_OR_PATH.pdf "Short explanation".

`-e` denotes erratum instead of revision.
By default, a dry run happens.
When you are ready, add `--do`.
"""

import argparse
import filetype
import os
import shutil
import ssl
import sys
import tempfile

from anthology.utils import (
    deconstruct_anthology_id,
    make_simple_element,
    indent,
    compute_hash,
    infer_url,
    is_newstyle_id,
)
from anthology.data import ANTHOLOGY_PDF

import lxml.etree as ET
import urllib.request

from datetime import datetime


def validate_file_type(path):
    """Ensure downloaded file mime type matches its extension (e.g., PDF)"""
    detected = filetype.guess(path)
    if detected is None or not detected.mime.endswith(detected.extension):
        mime_type = 'UNKNOWN' if detected is None else detected.mime
        print(
            f"FATAL: {args.anthology_id} file {path} has MIME type {mime_type}",
            file=sys.stderr,
        )
        sys.exit(1)


def download_file(source, dest):
    try:
        print(
            f"-> Downloading file from {source} to {dest}",
            file=sys.stderr,
        )
        with urllib.request.urlopen(source) as url, open(dest, mode="wb") as fh:
            fh.write(url.read())
    except ssl.SSLError:
        print(
            f"-> FATAL: An SSL error was encountered in downloading {source}.",
            file=sys.stderr,
        )
        sys.exit(1)


def main(args):
    def maybe_copy(file_from, file_to):
        if not args.dry_run:
            print("-> Copying from {} -> {}".format(file_from, file_to), file=sys.stderr)
            shutil.copy(file_from, file_to)
            os.chmod(file_to, 0o644)
        else:
            print(
                "-> DRY RUN: Copying from {} -> {}".format(file_from, file_to),
                file=sys.stderr,
            )

    change_type = "erratum" if args.erratum else "revision"
    change_letter = "e" if args.erratum else "v"

    print(f"Processing {change_type} to {args.anthology_id}...")

    # TODO: make sure path exists, or download URL to temp file
    if args.path.startswith("http"):
        _, input_file_path = tempfile.mkstemp()
        download_file(args.path, input_file_path)
    else:
        input_file_path = args.path

    validate_file_type(input_file_path)

    collection_id, volume_id, paper_id = deconstruct_anthology_id(args.anthology_id)
    paper_extension = args.path.split(".")[-1]

    # The new version
    revno = None

    with open(input_file_path, "rb") as f:
        checksum = compute_hash(f.read())

    # Files for old-style IDs are stored under anthology-files/pdf/P/P19/*
    # Files for new-style IDs are stored under anthology-files/pdf/2020.acl/*
    if is_newstyle_id(args.anthology_id):
        venue_name = collection_id.split(".")[1]
        output_dir = os.path.join(args.anthology_dir, "pdf", venue_name)
    else:
        output_dir = os.path.join(
            args.anthology_dir, "pdf", collection_id[0], collection_id
        )

    # Make sure directory exists
    if not os.path.exists(output_dir):
        print(f"-> Creating directory {output_dir}", file=sys.stderr)
        os.makedirs(output_dir)

    canonical_path = os.path.join(output_dir, f"{args.anthology_id}.pdf")

    # Update XML
    xml_file = os.path.join(
        os.path.dirname(sys.argv[0]), "..", "data", "xml", f"{collection_id}.xml"
    )
    tree = ET.parse(xml_file)
    paper = tree.getroot().find(f"./volume[@id='{volume_id}']/paper[@id='{paper_id}']")
    if paper is not None:
        revisions = paper.findall(change_type)
        revno = 1 if args.erratum else 2
        for revision in revisions:
            revno = int(revision.attrib["id"]) + 1

        if not args.dry_run:
            # Update the URL hash on the <url> tag
            url = paper.find("./url")
            if url is not None:
                url.attrib["hash"] = checksum

            if not args.erratum and revno == 2:
                if paper.find("./url") is not None:
                    current_version_url = infer_url(paper.find("./url").text) + ".pdf"

                # Download original file
                # There are no versioned files the first time around, so create the first one
                # (essentially backing up the original version)
                revised_file_v1_path = os.path.join(
                    output_dir, f"{args.anthology_id}{change_letter}1.pdf"
                )

                download_file(current_version_url, revised_file_v1_path)
                validate_file_type(revised_file_v1_path)

                with open(revised_file_v1_path, "rb") as f:
                    old_checksum = compute_hash(f.read())

                # First revision requires making the original version explicit
                revision = make_simple_element(
                    change_type,
                    None,
                    attrib={
                        "id": "1",
                        "href": f"{args.anthology_id}{change_letter}1",
                        "hash": old_checksum,
                    },
                    parent=paper,
                )

            revision = make_simple_element(
                change_type,
                args.explanation,
                attrib={
                    "id": str(revno),
                    "href": f"{args.anthology_id}{change_letter}{revno}",
                    "hash": checksum,
                    "date": args.date,
                },
                parent=paper,
            )
            indent(tree.getroot())

            tree.write(xml_file, encoding="UTF-8", xml_declaration=True)
            print(
                f'-> Added {change_type} node "{revision.text}" to XML', file=sys.stderr
            )

    else:
        print(
            f"-> FATAL: paper ID {args.anthology_id} not found in the Anthology",
            file=sys.stderr,
        )
        sys.exit(1)

    revised_file_versioned_path = os.path.join(
        output_dir, f"{args.anthology_id}{change_letter}{revno}.pdf"
    )

    # Copy the file to the versioned path
    maybe_copy(input_file_path, revised_file_versioned_path)

    # Copy it over the canonical path
    if not args.erratum:
        maybe_copy(input_file_path, canonical_path)

    if args.path.startswith("http"):
        os.remove(input_file_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "anthology_id", help="The Anthology paper ID to revise (e.g., P18-1001)"
    )
    parser.add_argument(
        "path", type=str, help="Path to the revised paper ID (can be URL)"
    )
    parser.add_argument("explanation", help="Brief description of the changes.")
    parser.add_argument(
        "--erratum",
        "-e",
        action="store_true",
        help="This is an erratum instead of a revision.",
    )
    now = datetime.now()
    today = f"{now.year}-{now.month:02d}-{now.day:02d}"
    parser.add_argument(
        "--date",
        "-d",
        type=str,
        default=today,
        help="The date of the revision (ISO 8601 format)",
    )
    parser.add_argument(
        "--dry-run", "-n", action="store_true", default=False, help="Just a dry run."
    )
    parser.add_argument(
        "--anthology-dir",
        default=os.path.join(os.environ["HOME"], "anthology-files"),
        help="Anthology web directory root.",
    )
    args = parser.parse_args()

    main(args)
