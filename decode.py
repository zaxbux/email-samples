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

mimetypes.add_type('message/delivery-status', '.eml')

# filename ":"" = "~" and "?" = "$"

def get_parent_dir(path: str) -> str:
    return os.path.dirname(os.path.realpath(path))

_DIR = get_parent_dir(__file__)

def rfc2046_boundary_to_windows(filename: str):
    """
    Takes an rfc2046 boundary delimiter and converts it to a windows-safe file name.
    """
    return filename.replace(':', '~').replace('?', '$')

def clean(path: str):
    """
    Creates directories for parts of samples.
    Deletes any existing parts (files ending in [subject].eml.[boundary].[content-type]).
    """
    if not os.path.isdir(path):
        os.mkdir(path)

    for filename in glob.glob(f"{glob.escape(path)}/[0-9].*.*"):
        os.remove(filename)
        print(f"\tremoved \"{os.path.basename(filename)}\"")

def get_message_content(message: EmailMessage):
    """
    Returns the content of a message. This is either the whole message, or the decoded payload.
    Also minifies HTML content.
    """
    if message.is_multipart():
        data = message.as_bytes()
    else:
        data = message.get_payload(decode=True)

    if message.get_content_type() == 'text/html':
        # Minify HTML
        html = data.decode('utf-8')
        html = minify_html.minify(html,
            minify_css=True,
            minify_js=True,
            keep_comments=True,
            keep_html_and_head_opening_tags=True)
        data = html.encode('utf-8')

    return data

def write_message(message: EmailMessage, path, part_boundary):
    content_type = message.get_content_type()
    extension = mimetypes.guess_extension(content_type)
    filename = rfc2046_boundary_to_windows(part_boundary)

    if message.is_attachment():
        # Use attachment name as part of the file name
        filename, extension = os.path.splitext(message.get_filename())

    file_count = len(glob.glob(f'{glob.escape(path)}/[0-9].{glob.escape(filename)}.*'))
    filename = f'{path}/{file_count}.{filename}{extension}'
    content = get_message_content(message)

    with open(filename, 'xb') as fp:
        fp.write(content)
    print(f'\twrote {len(content)} bytes to {filename} ({content_type})')

def extract_from_message(message: EmailMessage, path: str, part_boundary: str = None):
    if message.get_content_maintype() == 'message':
        """
        Write message sub-payloads as one file, in addition to its parts.
        """
        write_message(message, path, part_boundary)
        if message.get_content_subtype() == 'delivery-status':
            """
            This message is reported as multipart, however it does not contain any content. Thus, it can be considered one message.
            Each payload is a group of fields, the first is the "per-message" group, followed by one or more "per-recipient" groups.
            See rfc3464 section 2.1
            """
            return

    if message.is_multipart():
        if message.get_boundary():
            part_boundary = message.get_boundary()
        for part in message.get_payload():
            extract_from_message(part, path, part_boundary)
    else:
        write_message(message, path, part_boundary)


def extract_from_file(path):
    with open(f'{path}.eml', 'r') as fp:
        message = email.message_from_file(fp, policy=email.policy.default)

    extract_from_message(message, f'{path}')

def main():
    # Recursively find .eml files and extract parts, deleting existing parts first.
    for filename in glob.glob(f"{_DIR}/*/{glob.escape('[sample]')} *.eml", recursive=True):
        directory = os.path.dirname(filename)
        basename = os.path.splitext(os.path.basename(filename))[0]

        print(f"Decoding \"{directory.split('/')[-1]}/{basename}.eml\"")

        path = f'{directory}/{basename}'
        clean(path)
        extract_from_file(path)
        print()

if __name__ == '__main__':
    main()
