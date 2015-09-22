# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import re
import sys


def getByUrl(url):
    resp = requests.get(url)
    if resp.status_code != 200:
        raise RuntimeError(u'Ошибка')
    return resp.content


def getSoupByHtml(html):
    return BeautifulSoup(html, 'html.parser')


def getSoupHtmlByUrl(url):
    return getSoupByHtml(getByUrl())

# из строки вида <tr><td><img src='\/shared\/site\/images\/check_icon_1.png' width='49' height='47'> <span>\u041a\u0438\u0435\u0432\u0441\u043a\u043e\u0435 \u043e\u0442\u0434\u0435\u043b\u0435\u043d\u0438\u0435 \u21163<\/span><\/td><td>\u0443\u043b. \u0421\u0442\u0430\u0440\u043e\u0432\u043e\u043a\u0437\u0430\u043b\u044c\u043d\u0430\u044f, 13<\/td><td><\/td><td><\/td><td>\u043a\u0440\u0443\u0433\u043b\u043e\u0441\u0443\u0442\u043e\u0447\u043d\u043e<\/td>
# получаем нормальную html-строку
def decodeUniCharsAndSlashed(s):
    s2 = re.sub(r'\\u([a-fA-F0-9]{4})', lambda m: unichr(int(m.group(1), 16)), s)
    s2 = s2.replace('\\/', '/')
    import cgi_unescape
    return cgi_unescape.unescape(s2)


# получая на вход строку вида
# curl 'http://www.mbank.kiev.ua/jscripts/ajax/list_serialize.php?city=1000%3F%3E&q=&type%5B%5D=1&type%5B%5D=2&type%5B%5D=3&type%5B%5D=4&type%5B%5D=5&lang=ru' -H 'X-Requested-With: XMLHttpRequest' --compressed
# шлет аналогичный запрос с использованием requests и ответ (response объект из requests) возвращает
def getRequestsResponseByCurlBashCommand(curl_bash_command):

    # Преобразовываем в список аргументов, в кавычках строка идет как один аргумент, даже если внутри нее пробел
    arg_index = 0
    curl_parts = curl_bash_command.split(' ')
    cur_parts_quoted = []
    while(arg_index!= len(curl_parts)):

        # если пробел внутри строки
        if curl_parts[arg_index].startswith("'"):
            cmd = curl_parts[arg_index]
            while not curl_parts[arg_index].endswith("'"):
                arg_index += 1
                cmd += " " + curl_parts[arg_index]
            cur_parts_quoted.append(cmd[1:-1])
            arg_index += 1

        else:
            cur_parts_quoted.append(curl_parts[arg_index])
            arg_index += 1

    # Извлпекаем параметры
    url = cur_parts_quoted[1]
    headers = []
    arg_index = 2
    while(arg_index!= len(cur_parts_quoted)):

        # если заголовок
        if cur_parts_quoted[arg_index] == '-H':
            headers.append(cur_parts_quoted[arg_index + 1])
            arg_index += 2

        elif cur_parts_quoted[arg_index] == '--compressed':
            headers.append('Accept-Encoding: gzip, deflate')
            arg_index += 1

        else:
            raise RuntimeError(u'Unknown argument: ' + cur_parts_quoted[arg_index])

    headers_dict = dict((h.split(':', 1)[0], h.split(':', 1)[1].strip()) for h in headers)

    from requests import Request, Session
    s = Session()
    req = Request('get', url, headers=headers_dict)
    prepped = req.prepare()
    return s.send(prepped)


resp = getRequestsResponseByCurlBashCommand("curl 'http://www.mbank.kiev.ua/jscripts/ajax/list_serialize.php?city=1000%3F%3E&q=&type%5B%5D=1&type%5B%5D=2&type%5B%5D=3&type%5B%5D=4&type%5B%5D=5&lang=ru' -H 'X-Requested-With: XMLHttpRequest'")
soup = getSoupByHtml(decodeUniCharsAndSlashed(resp.content))

# Банкомат              1 184105402
# платежный терминал    2 184106974
# Рубринка банк         3,4,5 184105398

requestet_type_mbank_num = sys.argv[1].split(',')
requested_type_category = sys.argv[2]

print """<?xml version="1.0" encoding="UTF-8"?>"""
print """<companies xmlns:xi="http://www.w3.org/2001/XInclude" version="2.1">"""

for row in soup.find_all(name = 'tr'):

    tds = row.find_all(name='td')

    type_png = row.find(name='img').get('src')
    if any([type_png.endswith('{0}.png'.format(n)) for n in requestet_type_mbank_num]):

        company = u"""    <company>
        <name lang="ru">{name}</name>
        <address lang="ru">{address}</address>
        <phone>
            <ext/><type>phone</type>
            <number>{phone}</number>
            <info/>
        </phone>
        <working-time lang="ru">{wtime}</working-time>
        <rubric-id>{rubric}</rubric-id>
    </company>
"""

        print company.format(
            name = unicode(tds[0].find(name=u'span').get_text()),
            address = unicode(tds[1].get_text()),
            phone = unicode(tds[3].get_text()),
            wtime = unicode(tds[4].get_text()),
            rubric = unicode(requested_type_category)
        )

print """</companies>"""
