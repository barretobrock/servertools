#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import datetime
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import imaplib
import mimetypes
from smtplib import SMTP
from typing import List


class Email:
    """
    Performs email-related activities
    """
    def __init__(self, un, pw, log):
        """Connect to account"""
        self.un = un
        self.pw = pw
        self.log = log
        self.smtpserver = SMTP('smtp.gmail.com', 587)
        self.imapserver = imaplib.IMAP4_SSL('imap.gmail.com', imaplib.IMAP4_SSL_PORT)

    def connect_for_sending(self):
        """Connect to the SMTP server for sending emails"""
        self.smtpserver.ehlo()
        self.smtpserver.starttls()
        self.smtpserver.login(self.un, self.pw)
        self.log.debug('Connected with email server.')

    def connect_for_reading(self):
        """Connect to the IMAP server to read emails"""
        self.imapserver.login(self.un, self.pw)

    def search(self, label='inbox', mail_filter='ALL'):
        """Get email objects based on a filter"""
        self.connect_for_reading()
        self.imapserver.select(label)
        mail_status, mail_data = self.imapserver.uid('search', None, mail_filter)
        # Convert list of ids from bytes to string, then split
        mail_ids = mail_data[0].decode('utf8').split(' ')
        # Get most recent message and check the date
        mail_id = mail_ids[-1]
        email_status, email_data = self.imapserver.uid('fetch', mail_id, "(RFC822)")
        raw_email = email_data[0][1]
        # Parse email from bytes into EmailMessage object for easy data extraction
        emailobj = email.message_from_bytes(raw_email)
        # Check if data of email object was today
        emaildate = datetime.datetime.strptime(emailobj['Date'][:-6], '%a, %d %b %Y %H:%M:%S')
        today = datetime.datetime.now()
        if emaildate.timestamp() > today.timestamp():
            # Email is current. Return elements
            return emailobj

    def _sendmail_routine(self, email_to, email_object):
        self.log.debug('Communicating with server.')
        try:
            self.connect_for_sending()
            self.smtpserver.sendmail(self.un, email_to, email_object.as_string())
            self.log.debug('Message sent.')
            self.smtpserver.quit()
        except TimeoutError:
            self.log.exception('Connection with server timed out.')
        except:
            self.log.exception('Could not connect with email server.')

    def forward(self, email_to, email_object):
        """Command to forward an email"""
        email_object.replace_header('From', self.un)
        email_object.replace_header('To', email_to)
        self._sendmail_routine(email_to=email_to, email_object=email_object)

    def send(self, email_to, subject, body, attachment_paths: List[str] = None):
        """Command to package and send email"""
        self.log.debug('Beginning email process.')
        msg = MIMEMultipart()
        msg["From"] = self.un
        msg["To"] = ', '.join([email_to])
        msg["Subject"] = subject
        msg.preamble = body
        if attachment_paths is not None:
            self.log.debug('Encoding any attachments')
            for attachment_path in attachment_paths:
                ctype, encoding = mimetypes.guess_type(attachment_path)
                if ctype is None or encoding is not None:
                    ctype = "application/octet-stream"
                maintype, subtype = ctype.split("/", 1)
                if maintype == 'text':
                    with open(attachment_path) as f:
                        attachment = MIMEText(f.read(), _subtype=subtype)
                else:
                    with open(attachment_path) as f:
                        attachment = MIMEBase(maintype, subtype)
                        attachment.set_payload(f.read())
                        encoders.encode_base64(attachment)
                attachment.add_header("Content-Disposition", 'attachment', filename=os.path.basename(attachment_path))
                msg.attach(attachment)
        self._sendmail_routine(email_to=email_to, email_object=msg)
