import re
from typing import Any, Dict, List, Tuple

from .entityDefinition import *

rusLettersString = "АаБбВвГгДдЕеЁёЖжЗзИиЙйКкЛлМмНнОоПпРрСсТтУуФфХхЦцЧчШшЩщъЫыьЭэЮюЯяЬ"
actionPattern = "[()\"']?[\s]*\$\$[\s]*[Aa][Cc][Tt][_a-zA-Z0-9]*[\s]*\$\$[\s]*[()\"']?"

# add descriptor, actually not just placeholder, it's a placeholder detector, members' order matter in a group
placeholderPattern = "%+(?:(?:[a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)+%+)|(?:[a-z](?:\[[a-z0-9,]*?\])?))[\s]*"
scriptPlaceHolderPattern = "(?<!\$)\$[a-zA-Z0-9_" + \
    rusLettersString + "]+[ ,.!?\"]?"
lineBreakPattern = r"(?:\n|\\n)+"
allInOnePattern = '(?:' + actionPattern + ')|(?:' + placeholderPattern + \
    ')|(?:' + scriptPlaceHolderPattern + ')|(?:' + lineBreakPattern + ')'

rusLetCpl = re.compile("[" + rusLettersString + "]")
actionCpl = re.compile(actionPattern)
placeholderCpl = re.compile(placeholderPattern)
scriptCpl = re.compile(scriptPlaceHolderPattern)
allSeparateTextCpl = re.compile(allInOnePattern)

noLettersPattern = re.compile("[^a-zA-Z"+rusLettersString+"]*")


def getRecommendLangText(entity: TextEntity, targetLang: str) -> Tuple[str]:
    blackList = []
    for lang in entity.texts:
        if lang == "text":
            return (lang, entity.texts[lang])
    recOrder = ["eng", "rus", "ukr"]
    for lang in recOrder:
        #
        if lang == targetLang or lang not in entity.texts:
            continue
        if not lang == "rus" and entity.texts[lang].strip().startswith("==="):
            continue
        if lang == "eng" and len(rusLetCpl.findall(entity.texts[lang])) > 0:
            blackList.append(lang)
            continue

        # this lang passed all test
        return (lang, entity.texts[lang])

    # insurance
    for lang in entity.texts and lang not in blackList:
        return (lang, entity.texts[lang])

    assert 1 > 2, "No Recommended Language"


def shouldPieceBeTranslated(piece: str) -> bool:
    res = noLettersPattern.fullmatch(piece)
    return res is None


def escapeXmlContentString(text: str) -> str:
    replaced = re.sub('&', '&amp;', text)
    replaced = re.sub('"', '&quot;', replaced)
    replaced = re.sub("'", '&apos;', replaced)
    replaced = re.sub('<', '&lt;', replaced)
    return replaced


def normalize_xml_string(xmlStr: str) -> str:
    replaced = re.sub('&[\s]+amp;', '&amp;', xmlStr)
    replaced = re.sub('&[\s]+lt;', '&lt;', replaced)
    replaced = re.sub(
        '&(?!ensp;|emsp;|nbsp;|lt;|gt;|amp;|quot;|copy;|reg;|trade;|times;|divide;)', '&amp;', replaced)
    replaced = re.sub('<\?xml[^>]+encoding=[^>]+\?>', '', replaced)
    replaced = re.sub('<!--[\s\S]*?-->', '', replaced)

    # that's all I can do to convert < in xml, if still not work, I will use regex or give up
    replaced = re.sub('<(?![a-zA-Z/])', '&lt;', replaced)

    if not replaced.strip().startswith("<string_table>"):
        replaced = "<string_table>" + replaced + "</string_table>"

    # I cant believe in some case , there are half a string tag after the end of </string_table>
    replaced = re.sub(r"</string_table>[\s\S]+", "</string_table>", replaced)
    return replaced


def getEncodingDeclaration(xmlStr: str) -> str:
    dec = re.compile("<\?xml[^>]+encoding=([^>]+)\?>")
    resDec = dec.findall(xmlStr)
    if len(resDec) > 0:
        return re.sub(r'[\'"\s]', '', resDec[0])
    else:
        return None


def cutText(text: str) -> List[Dict[str, str]]:
    seps = allSeparateTextCpl.findall(text)
    pieces = allSeparateTextCpl.split(text)
    assert len(pieces) == len(seps) + \
        1, "separator and pieces count won't match"

    res = []
    for i in range(len(pieces)):
        if shouldPieceBeTranslated(pieces[i]):
            res.append({
                "needTrans": True,
                "content": pieces[i]
            })
        else:
            res.append({
                "needTrans": False,
                "content": pieces[i]
            })
        if(i < len(seps)):
            washed = re.sub(r"(?<=\$\$)[\s]*(?=[_a-zA-Z0-9])", "", seps[i])
            washed = re.sub(r"(?<=[_a-zA-Z0-9])[\s]*(?=\$\$)", "", washed)
            res.append({
                "needTrans": False,
                "content": washed
            })

    return res