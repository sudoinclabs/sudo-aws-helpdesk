# -*- coding: utf-8 -*-
import mailbox
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import base64
import datetime
import dateutil
import email
import email.policy
import hashlib
import hmac
import lxml
import logging
import pytz
import re
import socket
import time
import threading

from collections import namedtuple
from email.message import EmailMessage
from email import message_from_string, policy
from lxml import etree
from werkzeug import urls
from xmlrpc import client as xmlrpclib

from odoo import models, fields, api

import logging
_logger = logging.getLogger(__name__)

class InheritMailSUDOMessage(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.model
    def message_process(self, model, message, custom_values=None,
                        save_original=False, strip_attachments=False,
                        thread_id=None):

        if isinstance(message, xmlrpclib.Binary):
            message = bytes(message.data)
        if isinstance(message, str):
            message = message.encode('utf-8')
        sudo_message = email.message_from_bytes(message, policy=email.policy.SMTP)
        if "@amazon.com" in sudo_message['From'] \
            or sudo_message['From'] == 'Hameedullah Khan <h@hameedullah.com>':
            try:
                _logger.debug("Inside Subject")
                sudo_case_id = False
                sudo_subject = sudo_message['Subject']
                if sudo_subject.lower().index("[case") >= 0:
                    _logger.debug("Finding Case")
                    sudo_case_tokens = sudo_subject.lower().split("[case")
                    _logger.debug(sudo_case_tokens)
                    sudo_case_tokens = sudo_case_tokens[1].split("]")
                    _logger.debug(sudo_case_tokens)
                    sudo_case_tokens = sudo_case_tokens[0].strip()
                    _logger.debug(sudo_case_tokens)
                    sudo_case_id = sudo_case_tokens

                if sudo_subject.lower().index("Resolved") >= 0:
                    _logger.debug("Resolved: Finding Case")
                    sudo_case_tokens = sudo_subject.lower().split("Resolved")
                    _logger.debug(sudo_case_tokens)
                    sudo_case_tokens = sudo_case_tokens[1].split(":")
                    _logger.debug(sudo_case_tokens)
                    sudo_case_tokens = sudo_case_tokens[0].strip()
                    _logger.debug(sudo_case_tokens)
                    sudo_case_id = sudo_case_tokens

                if sudo_subject.lower().index("Attention required on case") >= 0:
                    _logger.debug("Attention required on case: Finding Case")
                    sudo_case_tokens = sudo_subject.lower().split(":")
                    _logger.debug(sudo_case_tokens)
                    sudo_case_tokens = sudo_case_tokens[0].split()
                    _logger.debug(sudo_case_tokens)
                    sudo_case_tokens = sudo_case_tokens[-1].strip()
                    _logger.debug(sudo_case_tokens)
                    sudo_case_id = sudo_case_tokens


                if sudo_case_id:
                    sudo_helpdesk_ticket = self.env['helpdesk.ticket'].search([('aws_ticket_number', '=', sudo_case_id)], limit=1)

                    sudo_follower_ids = []
                    for sudo_f_id in sudo_helpdesk_ticket.message_follower_ids:
                        if sudo_f_id.partner_id.user_ids:
                            sudo_follower_ids.append(sudo_f_id.partner_id.id)
                    sudo_body = ""

                    if sudo_message.is_multipart():
                        for part in sudo_message.walk():
                            ctype = part.get_content_type()
                            cdispo = str(part.get('Content-Disposition'))

                            # skip any text/plain (txt) attachments
                            if ctype == 'text/plain' and 'attachment' not in cdispo:
                                sudo_body = part.get_payload(decode=True)  # decode
                                break
                    # not multipart - i.e. plain text, no attachments, keeping fingers crossed
                    else:
                        sudo_body = sudo_message.get_payload(decode=True)
                    #sudo_body = str(sudo_body)
                    _logger.debug(sudo_body)
                    sudo_helpdesk_ticket.message_post(
                        subject =  "AWS Response Added on: %s" % sudo_helpdesk_ticket.name,
                        body = "%s" % "<br>".join(sudo_body.decode().splitlines()),
                        message_type='comment',
                        subtype_id=self.env.ref('mail.mt_note').id,
                        partner_ids=sudo_follower_ids
                    )
                    return None
            except:
                pass # If our logic fails we don't want stop email processing like normal
        result = super(InheritMailSUDOMessage, self).message_process(model, message, custom_values,
                        save_original, strip_attachments,
                        thread_id)
        return result
class SudoAWSHelpdesk(models.Model):
    _inherit = 'helpdesk.ticket'

    aws_ticket_number = fields.Char('AWS Ticket Number')
