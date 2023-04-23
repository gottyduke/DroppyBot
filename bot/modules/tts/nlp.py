import datetime
import enum
import re

from shared import CogBase
import modules.tts.session as session

import discord
import urlextract

# global
_token_pair = {
    # names
    289495654672367616: '多罗皮',
    899476797392052264: '清源',
    674647260016934942: '波吉亚',
    893586730173755463: '纳必的',
    353710123878973482: '黄老师',
    704492269428015264: '踹哈',
    772171966806753333: '大福',
    1074905338869985280: '小福',
    689961666955444287: '叶紫',
    825147169543028787: '牛牛子',
    917164148297707520: '老八',
    946057811236896770: '秦陌',
    1085845039441256468: '济师傅',
    378384809707175936: '拉服拉妹',
    922036157255122965: '西肉',
    184022605743915009: '丹少',
    650787841185546264: '泽兜'
}
active_token_pair = _token_pair


def alias_name(user_id):
    for token, alias in active_token_pair.items():
        if token == user_id:
            return alias
    return None


# export
class SpeechType(enum.Enum):
    UNDEF = 0,
    TEXT = 1,
    EMOJI = 2,
    URL = 3,
    MENTION = 4,
    REPLY = 5,


class Speech():
    speaker: str
    content: str
    timestamp: datetime
    type: SpeechType

    def __init__(self, speaker, content, timestamp, type):
        self.speaker = speaker
        self.content = content
        self.timestamp = timestamp
        self.type = type


async def process(message: discord.Message):
    valid_speech = []
    speaker = message.author
    alias = alias_name(speaker.id)
    if alias is None:
        alias = speaker.name

    content = message.content
    speech_type = SpeechType.TEXT

    # refer
    if message.reference is not None and message.reference.resolved is not None:
        recepient = message.reference.resolved.author
        rec_alias = alias_name(recepient.id)
        if rec_alias is None:
            rec_alias = recepient.name
        valid_speech.append(
            Speech(alias, rec_alias, message.created_at, SpeechType.REPLY))

    lex = re.findall('<.*?>', content)
    for em in lex:
        # emoji
        if em[1] == ':':
            # singular speech
            valid_speech.append(
                Speech(alias, em[1:-1], message.created_at, SpeechType.EMOJI))

            content = content.replace(em, '')
        # mentions
        elif em[1] == '@':
            mention = shared.bot.get_user(int(em[2:-1]))
            mention_alias = alias_name(mention.id)
            if mention_alias is None:
                mention_alias = mention.name

            # singular speech
            if len(lex) == 1:
                valid_speech.append(
                    Speech(alias, mention_alias, message.created_at,
                           SpeechType.MENTION))
                content = content.replace(em, '')
            else:
                content = content.replace(em, mention_alias)
        elif em[1] == '#':
            content = content.replace(em, '')

    # urls
    ext = urlextract.URLExtract()
    urls = ext.find_urls(content, with_schema_only=True)
    for url in urls:
        if len(urls) == 1:
            valid_speech.append(
                Speech(alias, url, message.created_at, SpeechType.URL))
        content = content.replace(url, '')

    # text
    if not content.isspace() and content != '':
        valid_speech.append(
            Speech(alias, content.strip(), message.created_at, speech_type))

    return valid_speech
