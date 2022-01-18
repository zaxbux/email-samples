#!/usr/bin/env python3
"""
This script decodes a multipart/* MIME message and splits it into its parts.
"""

from email.message import EmailMessage
import os
import glob
import email
import email.policy
import mimetypes
import minify_html

# filename ":"" = "~" and "?" = "$"

def get_parent_dir(path: str) -> str:
    return os.path.dirname(os.path.realpath(path))

_DIR = get_parent_dir(__file__)

def rfc2046_boundary_to_windows(filename: str):
    """
    Takes an rfc2046 boundary delimiter and converts it to a windows-safe file name.
    """
    return filename.replace(':', '~').replace('?', '$')

def clean(directory, basename):
    """
    Deletes any existing parts (files ending in [subject].eml.[boundary].[content-type]).
    """
    for filename in glob.glob(f'{directory}/{basename}.?*.?*'):
        os.remove(filename)

def save_part(directory, basename, boundary, message: EmailMessage):
    content_type = message.get_content_type()
    boundary = rfc2046_boundary_to_windows(boundary)[2:]
    ext = mimetypes.guess_extension(content_type)

    with open(f'{directory}/{basename}.{boundary}{ext}', 'wb+') as fp:
        data: bytes = message.get_payload(decode=True)

        if content_type == 'text/html':
            data_str = data.decode('utf-8')
            data_str: str = minify_html.minify(data_str, minify_css=True, minify_js=True, keep_comments=True)
            data = data_str.encode('utf-8')

        fp.write(data)

def extract(directory, basename):
    with open(f'{directory}/{basename}', 'r') as fp:
        message = email.message_from_file(fp, policy=email.policy.default)

    boundary = None

    for part in message.walk():
        if part.get_content_maintype() == 'multipart':
            boundary = part.get_boundary()
        else:
            save_part(directory, basename, boundary, part)

def main():
    # Recursively find .eml files and extract parts, deleting existing parts first.
    for filename in glob.glob(f'{_DIR}/**/*.eml', recursive=True):
        directory = os.path.dirname(filename)
        basename = os.path.basename(filename)
        clean(directory, basename)
        extract(directory, basename)

if __name__ == '__main__':
    main()
