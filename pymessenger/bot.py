import json
import os
from enum import Enum

import requests
from requests_toolbelt import MultipartEncoder

from pymessenger import utils

DEFAULT_API_VERSION = 16.0


class NotificationType(Enum):
    regular = "REGULAR"
    silent_push = "SILENT_PUSH"
    no_push = "NO_PUSH"


class TagType:
    confirmed_event_update = 'CONFIRMED_EVENT_UPDATE'
    post_purchase_update = 'POST_PURCHASE_UPDATE'
    account_update = 'ACCOUNT_UPDATE'
    human_agent = 'HUMAN_AGENT'


class Bot:
    def __init__(self, access_token, **kwargs):
        """
            @required:
                access_token
                page_id
            @optional:
                api_version
                app_secret
        """

        self.api_version = kwargs.get('api_version') or DEFAULT_API_VERSION
        self._num_api_version = float(self.api_version)
        self.app_secret = kwargs.get('app_secret')
        self.page_id = kwargs.get('page_id', "me")  # "me" is deprecated and removed though.
        self.graph_url = 'https://graph.facebook.com/v{0}'.format(self.api_version)
        self.access_token = access_token

    @property
    def auth_args(self):
        if not hasattr(self, '_auth_args'):
            auth = {
                'access_token': self.access_token
            }
            if self.app_secret is not None:
                appsecret_proof = utils.generate_appsecret_proof(self.access_token, self.app_secret)
                auth['appsecret_proof'] = appsecret_proof
            self._auth_args = auth
        return self._auth_args

    def send_recipient(self, recipient_id, payload, notification_type=NotificationType.regular):
        payload['recipient'] = {
            'id': recipient_id
        }
        payload['notification_type'] = notification_type.value
        return self.send_raw(payload)

    def send_message(self, recipient_id, message, notification_type=NotificationType.regular):
        if self._num_api_version >= 14.0:
            return self.send_message_api16plus(recipient_id, message, notification_type=notification_type)
        
        return self.send_recipient(recipient_id, {
            'message': message
        }, notification_type)
    
    # def send_message_api16plus(self, payload):
    def send_message_api16plus(self, recipient_id, message, notification_type=NotificationType.regular):
        ## modern API (2023) (src: https://developers.facebook.com/docs/messenger-platform/get-started#step-3--send-the-customer-a-message)
        # curl -i -X POST "https://graph.facebook.com/v14.0/PAGE-ID/messages
        # ?recipient={id:PSID}
        # &message={text:'You did it!'}
        # &messaging_type=RESPONSE
        # &access_token=PAGE-ACCESS-TOKEN"
        recipient_id = recipient_id.get("id")
        request_endpoint = '{0}/{1}/messages'.format(self.graph_url, self.page_id)
        params = {
            "recipient": recipient_id,
            "messaging_type": "RESPONSE",
            "message": message,
        }
        params.update(self.auth_args)
        
        response = requests.post(
            request_endpoint,
            params=params,
        )
        result = response.json()
        return result


    def send_tag_message(self, recipient_id, message, tag=TagType.human_agent,
                         notification_type=NotificationType.regular):
        """
        https://developers.facebook.com/docs/messenger-platform/send-messages/message-tags#sending
        :param recipient_id:
        :param message:
        :param tag:
        :param notification_type:
        :return:
        """
        return self.send_recipient(recipient_id, {
            'message': message,
            'messaging_type': 'MESSAGE_TAG',
            'tag': tag
        }, notification_type)

    def send_attachment(self, recipient_id, attachment_type, attachment_path,
                        notification_type=NotificationType.regular, is_reusable=True):
        """Send an attachment to the specified recipient using local path.
        Input:
            recipient_id: recipient id to send to
            attachment_type: type of attachment (image, video, audio, file)
            attachment_path: Path of attachment
        Output:
            Response from API as <dict>
        """
        file_type = f'''{attachment_type}/{attachment_path.split('.')[-1]}'''
        with open(attachment_path, 'rb') as f:
            file_data = f.read()
        payload = {
            'recipient': json.dumps({
                'id': recipient_id
            }),
            'notification_type': notification_type.value,
            'message': json.dumps({
                'attachment': {
                    'type': attachment_type,
                    'payload': {
                        'is_reusable': is_reusable
                    }
                }
            }),
            'filedata': (os.path.basename(attachment_path), file_data, file_type)
        }
        multipart_data = MultipartEncoder(payload)
        multipart_header = {
            'Content-Type': multipart_data.content_type
        }
        return requests.post(
            '{0}/{1}/messages'.format(self.graph_url, self.page_id),
            data=multipart_data,
            params=self.auth_args,
            headers=multipart_header
        ).json()

    def send_attachment_url(self, recipient_id, attachment_type, attachment_url,
                            notification_type=NotificationType.regular):
        """Send an attachment to the specified recipient using URL.
        Input:
            recipient_id: recipient id to send to
            attachment_type: type of attachment (image, video, audio, file)
            attachment_url: URL of attachment
        Output:
            Response from API as <dict>
        """
        return self.send_message(recipient_id, {
            'attachment': {
                'type': attachment_type,
                'payload': {
                    'url': attachment_url
                }
            }
        }, notification_type)

    def send_text_message(self, recipient_id, message, notification_type=NotificationType.regular):
        """Send text messages to the specified recipient.
        https://developers.facebook.com/docs/messenger-platform/send-api-reference/text-message
        Input:
            recipient_id: recipient id to send to
            message: message to send
        Output:
            Response from API as <dict>
        """
        return self.send_message(recipient_id, {
            'text': message
        }, notification_type)

    def send_generic_message(self, recipient_id, elements, notification_type=NotificationType.regular):
        """Send generic messages to the specified recipient.
        https://developers.facebook.com/docs/messenger-platform/send-api-reference/generic-template
        Input:
            recipient_id: recipient id to send to
            elements: generic message elements to send
        Output:
            Response from API as <dict>
        """
        return self.send_message(recipient_id, {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "generic",
                    "elements": elements
                }
            }
        }, notification_type)

    def send_button_message(self, recipient_id, text, buttons, notification_type=NotificationType.regular):
        """Send text messages to the specified recipient.
        https://developers.facebook.com/docs/messenger-platform/send-api-reference/button-template
        Input:
            recipient_id: recipient id to send to
            text: text of message to send
            buttons: buttons to send
        Output:
            Response from API as <dict>
        """
        return self.send_message(recipient_id, {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "button",
                    "text": text,
                    "buttons": buttons
                }
            }
        }, notification_type)

    def send_quick_replies_message(self, recipient_id, text, quick_replies, list_of_payloads=None):
        """
        Sends a list of text quick replies with an optional message (Default = " ")
        to send before sending the quick replies Payload and Message are optional,
        however, if no payload for a specific reply (i.e. None) or for all quick
        replies, the payload will be defined as the reply itself.
        https://developers.facebook.com/docs/messenger-platform/send-messages/quick-replies/#text
        Input:
            recipient_id: recipient id to send to
            text: text of message to send
            quick_replies: quick replies to send
        Output:
            Response from API as <dict>
        """
        quick_replies_list = []
        # if no payloads identified
        if not list_of_payloads:
            for reply in quick_replies:
                quick_replies_list.append({
                    'content_type': 'text',
                    'title': reply,
                    'payload': reply
                })
        # if payloads is identified
        else:
            for reply, payload in zip(quick_replies, list_of_payloads):
                # if some payload is not identified in the list
                if payload is None:
                    quick_replies_list.append({
                        'content_type': 'text',
                        'title': reply,
                        'payload': reply
                    })
                else:
                    quick_replies_list.append({
                        'content_type': 'text',
                        'title': reply,
                        'payload': payload
                    })
        return self.send_message(recipient_id, {
            'text': text,
            'quick_replies': quick_replies_list
        })

    def send_action(self, recipient_id, action, notification_type=NotificationType.regular):
        """Send typing indicators or send read receipts to the specified recipient.
        https://developers.facebook.com/docs/messenger-platform/send-api-reference/sender-actions

        Input:
            recipient_id: recipient id to send to
            action: action type (mark_seen, typing_on, typing_off)
        Output:
            Response from API as <dict>
        """
        return self.send_recipient(recipient_id, {
            'sender_action': action
        }, notification_type)

    def send_image(self, recipient_id, image_path, notification_type=NotificationType.regular, is_reusable=True):
        """Send an image to the specified recipient.
        Image must be PNG or JPEG or GIF (more might be supported).
        https://developers.facebook.com/docs/messenger-platform/send-api-reference/image-attachment
        Input:
            recipient_id: recipient id to send to
            image_path: path to image to be sent
        Output:
            Response from API as <dict>
        """
        return self.send_attachment(recipient_id, "image", image_path, notification_type, is_reusable=is_reusable)

    def send_image_url(self, recipient_id, image_url, notification_type=NotificationType.regular):
        """Send an image to specified recipient using URL.
        Image must be PNG or JPEG or GIF (more might be supported).
        https://developers.facebook.com/docs/messenger-platform/send-api-reference/image-attachment
        Input:
            recipient_id: recipient id to send to
            image_url: url of image to be sent
        Output:
            Response from API as <dict>
        """
        return self.send_attachment_url(recipient_id, "image", image_url, notification_type)

    def send_audio(self, recipient_id, audio_path, notification_type=NotificationType.regular):
        """Send audio to the specified recipient.
        Audio must be MP3 or WAV
        https://developers.facebook.com/docs/messenger-platform/send-api-reference/audio-attachment
        Input:
            recipient_id: recipient id to send to
            audio_path: path to audio to be sent
        Output:
            Response from API as <dict>
        """
        return self.send_attachment(recipient_id, "audio", audio_path, notification_type)

    def send_audio_url(self, recipient_id, audio_url, notification_type=NotificationType.regular):
        """Send audio to specified recipient using URL.
        Audio must be MP3 or WAV
        https://developers.facebook.com/docs/messenger-platform/send-api-reference/audio-attachment
        Input:
            recipient_id: recipient id to send to
            audio_url: url of audio to be sent
        Output:
            Response from API as <dict>
        """
        return self.send_attachment_url(recipient_id, "audio", audio_url, notification_type)

    def send_video(self, recipient_id, video_path, notification_type=NotificationType.regular):
        """Send video to the specified recipient.
        Video should be MP4 or MOV, but supports more (https://www.facebook.com/help/218673814818907).
        https://developers.facebook.com/docs/messenger-platform/send-api-reference/video-attachment
        Input:
            recipient_id: recipient id to send to
            video_path: path to video to be sent
        Output:
            Response from API as <dict>
        """
        return self.send_attachment(recipient_id, "video", video_path, notification_type)

    def send_video_url(self, recipient_id, video_url, notification_type=NotificationType.regular):
        """Send video to specified recipient using URL.
        Video should be MP4 or MOV, but supports more (https://www.facebook.com/help/218673814818907).
        https://developers.facebook.com/docs/messenger-platform/send-api-reference/video-attachment
        Input:
            recipient_id: recipient id to send to
            video_url: url of video to be sent
        Output:
            Response from API as <dict>
        """
        return self.send_attachment_url(recipient_id, "video", video_url, notification_type)

    def send_file(self, recipient_id, file_path, notification_type=NotificationType.regular):
        """Send file to the specified recipient.
        https://developers.facebook.com/docs/messenger-platform/send-api-reference/file-attachment
        Input:
            recipient_id: recipient id to send to
            file_path: path to file to be sent
        Output:
            Response from API as <dict>
        """
        return self.send_attachment(recipient_id, "file", file_path, notification_type)

    def send_file_url(self, recipient_id, file_url, notification_type=NotificationType.regular):
        """Send file to the specified recipient.
        https://developers.facebook.com/docs/messenger-platform/send-api-reference/file-attachment
        Input:
            recipient_id: recipient id to send to
            file_url: url of file to be sent
        Output:
            Response from API as <dict>
        """
        return self.send_attachment_url(recipient_id, "file", file_url, notification_type)

    def get_user_info(self, recipient_id, fields=None):
        """Getting information about the user
        https://developers.facebook.com/docs/messenger-platform/user-profile
        Input:
          recipient_id: recipient id to send to
        Output:
          Response from API as <dict>
        """
        params = {}
        if fields is not None and isinstance(fields, (list, tuple)):
            params['fields'] = ",".join(fields)

        params.update(self.auth_args)

        request_endpoint = '{0}/{1}'.format(self.graph_url, recipient_id)
        response = requests.get(request_endpoint, params=params)
        if response.status_code == 200:
            return response.json()

        return None

    
    def send_raw(self, payload):
        request_endpoint = '{0}/{1}/messages'.format(self.graph_url, self.page_id)
        response = requests.post(
            request_endpoint,
            params=self.auth_args,
            json=payload
        )
        result = response.json()
        return result

    def _send_payload(self, payload):
        """ Deprecated, use send_raw instead """
        return self.send_raw(payload)

    def set_get_started(self, gs_obj):
        """Set a get started button shown on welcome screen for first time users
        https://developers.facebook.com/docs/messenger-platform/reference/messenger-profile-api/get-started-button
        Input:
          gs_obj: Your formatted get_started object as described by the API docs
        Output:
          Response from API as <dict>
        """
        request_endpoint = '{0}/{1}/messenger_profile'.format(self.graph_url, self.page_id)
        response = requests.post(
            request_endpoint,
            params=self.auth_args,
            json=gs_obj
        )
        result = response.json()
        return result

    def set_persistent_menu(self, pm_obj):
        """Set a persistent_menu that stays same for every user. Before you can use this, make sure to have set a get started button.
        https://developers.facebook.com/docs/messenger-platform/reference/messenger-profile-api/persistent-menu
        Input:
          pm_obj: Your formatted persistent menu object as described by the API docs
        Output:
          Response from API as <dict>
        """
        request_endpoint = '{0}/{1}/messenger_profile'.format(self.graph_url, self.page_id)
        response = requests.post(
            request_endpoint,
            params=self.auth_args,
            json=pm_obj
        )
        result = response.json()
        return result

    def remove_get_started(self):
        """delete get started button.
        https://developers.facebook.com/docs/messenger-platform/reference/messenger-profile-api/#delete
        Output:
        Response from API as <dict>
        """
        delete_obj = {"fields": ["get_started"]}
        request_endpoint = '{0}/{1}/messenger_profile'.format(self.graph_url, self.page_id)
        response = requests.delete(
            request_endpoint,
            params=self.auth_args,
            json=delete_obj
        )
        result = response.json()
        return result

    def remove_persistent_menu(self):
        """delete persistent menu.
        https://developers.facebook.com/docs/messenger-platform/reference/messenger-profile-api/#delete
        Output:
        Response from API as <dict>
        """
        delete_obj = {"fields": ["persistent_menu"]}
        request_endpoint = '{0}/{1}/messenger_profile'.format(self.graph_url, self.page_id)
        response = requests.delete(
            request_endpoint,
            params=self.auth_args,
            json=delete_obj
        )
        result = response.json()
        return result
