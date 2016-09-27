"""Simplified interface to sending email via SMTP."""
__version__ = '0.0.4'

import logging
import smtplib
from email import Encoders
from email.Header import Header
from email.MIMEBase import MIMEBase
from email.MIMEImage import MIMEImage
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.Utils import COMMASPACE, formatdate

log = logging.getLogger(__name__)


def connect(host, port=587, username=None, password=None, secure=True):
    log.debug('Connecting to SMTP server: %s:%s', host, port)
    server = smtplib.SMTP(host, int(port))
    try:
        server.ehlo()

        if secure:
            server.starttls()

        if username:
            server.login(username, password)
    except Exception:
        server.close()

    return Connection(server)


class Connection(object):
    def __init__(self, server):
        self.server = server

    def send(self, doc):
        msg = create_message(doc)

        to_addresses = (doc.get('to', []) +
                        doc.get('cc', []) +
                        doc.get('bcc', []))

        for r in to_addresses:
            log.debug('Sending email to %s', r)
            self.server.sendmail(doc['from'], r, msg)

    def close(self):
        if self.server is not None:
            try:
                self.server.close()
            finally:
                self.server = None

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()


def create_message(doc):
    msg_root = MIMEMultipart('related')
    add_header(msg_root, 'Subject', doc['subject'])
    add_header(msg_root, 'From', doc['from'])

    if doc.get('to'):
        add_header(msg_root, 'To', COMMASPACE.join(doc['to']))

    if doc.get('cc'):
        add_header(msg_root, 'CC', COMMASPACE.join(doc['cc']))

    if doc.get('bcc'):
        add_header(msg_root, 'BCC', COMMASPACE.join(doc['bcc']))

    msg_root['Date'] = formatdate(localtime=True)
    msg_root.preamble = 'This is a multi-part message in MIME format.'

    msg_alt = MIMEMultipart('alternative')
    msg_root.attach(msg_alt)

    if doc.get('text'):
        if contains_nonascii_characters(doc['text']):
            msg_text = MIMEText(doc['text'].encode('utf-8'), 'plain', 'utf-8')
        else:
            msg_text = MIMEText(doc['text'], 'plain')
            msg_alt.attach(msg_text)

    if doc.get('html'):
        if contains_nonascii_characters(doc['html']):
            msg_text = MIMEText(doc['html'].encode('utf-8'), 'html', 'utf-8')
        else:
            msg_text = MIMEText(doc['html'], 'html')
            msg_alt.attach(msg_text)

    for image in doc.get('images', []):
        msg_img = MIMEImage(image['content'])
        add_header(msg_img, 'Content-ID', image['name'])
        add_header(msg_img, 'Content-Disposition', 'inline')
        msg_root.attach(msg_img)

    for attach in doc.get('attachments', []):
        raw_content = attach['content']
        msg_attach = MIMEBase('application', 'octet-stream')
        msg_attach.set_payload(raw_content)
        Encoders.encode_base64(msg_attach)
        add_header(msg_attach, 'Content-Disposition',
                   'attachment; filename="%s"' % attach['name'])
        msg_root.attach(msg_attach)

    return msg_root.as_string()


def add_header(message, name, value):
    if contains_nonascii_characters(value):
        message[name] = Header(value, 'utf-8')
    else:
        message[name] = value
    return message


def contains_nonascii_characters(str):
    return not all(ord(c) < 128 for c in str)
