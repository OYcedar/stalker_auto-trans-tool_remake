"""
Author: Vincent Young
Date: 2023-04-27 00:44:01
LastEditors: Vincent Young
LastEditTime: 2023-05-21 03:58:18
FilePath: /PyDeepLX/PyDeepLX/PyDeepLX.py
Telegram: https://t.me/missuo

Copyright © 2023 by Vincent, All Rights Reserved. 
"""
import random
import time
import json
import httpx
import re


deeplAPI = "https://www2.deepl.com/jsonrpc"
headers = {
    "Content-Type": "application/json",
    "Accept": "*/*",
    "x-app-os-name": "iOS",
    "x-app-os-version": "16.3.0",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "x-app-device": "iPhone13,2",
    "User-Agent": "DeepL-iOS/2.9.1 iOS 16.3.0 (iPhone13,2)",
    "x-app-build": "510265",
    "x-app-version": "2.9.1",
    "Connection": "keep-alive",
}


class TooManyRequestsException(Exception):
    "Raised when there is a 429 error"

    def __str__(self):
        return "PyDeepLX Error: Too many requests, your IP has been blocked by DeepL temporarily, please don't request it frequently in a short time."


def getICount(translateText) -> int:
    return translateText.count("i")


def getRandomNumber() -> int:
    random.seed(time.time())
    num = random.randint(8300000, 8399998)
    return num * 1000


def getTimestamp(iCount: int) -> int:
    ts = int(time.time() * 1000)

    if iCount == 0:
        return ts

    iCount += 1
    return ts - ts % iCount + iCount


def deeplTranslate(
    text,
    sourceLang="auto",
    targetLang="en",
    numberAlternative=0,
    printResult=False,
    proxies=None,
    postProcess=None
):
    iCount = getICount(text)
    id = getRandomNumber()

    numberAlternative = max(min(3, numberAlternative), 0)

    sents = cutSentenceWithLineEnds(text)
    texts = []
    for txt in sents:
        texts.append({"text": txt.strip(), "requestAlternatives": numberAlternative})

    postData = {
        "jsonrpc": "2.0",
        "method": "LMT_handle_texts",
        "id": id,
        "params": {
            "texts": texts,
            "splitting": "newlines",
            "lang": {
                "source_lang_user_selected": sourceLang,
                "target_lang": targetLang,
            },
            "timestamp": getTimestamp(iCount),
            "commonJobParams": {
                "wasSpoken": False,
                "transcribe_as": "",
            },
        },
    }
    postDataStr = json.dumps(postData, ensure_ascii=False)

    if (id + 5) % 29 == 0 or (id + 3) % 13 == 0:
        postDataStr = postDataStr.replace('"method":"', '"method" : "', -1)
    else:
        postDataStr = postDataStr.replace('"method":"', '"method": "', -1)

    # Add proxy (e.g. proxies='socks5://127.0.0.1:7890')
    with httpx.Client(proxies=proxies) as client:
        resp = client.post(url=deeplAPI, data=postDataStr, headers=headers)
        respStatusCode = resp.status_code

        if respStatusCode == 429:
            raise TooManyRequestsException

        if respStatusCode != 200:
            print("Error", respStatusCode)
            return

        respText = resp.text
        respJson = json.loads(respText)

        if numberAlternative <= 1:
            targetText = ""
            # for ent in respJson["result"]["texts"]:
            #     targetText = targetText+ent["text"]
            for i in range(len(respJson["result"]["texts"])):
                ent = respJson["result"]["texts"][i]["text"]
                if postProcess != None:
                    ent = postProcess(sents[i], ent)
                targetText = targetText+ent    
            if printResult:
                print(targetText)
            return targetText

        targetTextArray = []
        for item in respJson["result"]["texts"][0]["alternatives"]:
            targetTextArray.append(item["text"])
            if printResult:
                print(item["text"])

        return targetTextArray


def cutSentenceWithLineEnds(text: str, lineEnds: list[str] = ["?", ".", "!"]) -> list[str]:
        lineEndPtn = re.compile("["+"".join(lineEnds)+"]+")
        seps = lineEndPtn.findall(text)
        if len(seps) == 0:
            return [text]
        pieces = lineEndPtn.split(text)
        assert len(pieces) == len(seps) + \
            1, "separator and pieces count won't match"
        sentences = []
        for i in range(len(seps)):
            sentences.append(pieces[i]+seps[i])
        if len(sentences) > 0 and len(pieces[-1].strip())>0:
            sentences.append(pieces[-1])
        return sentences
