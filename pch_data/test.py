from bs4 import BeautifulSoup
import urllib.parse, requests, re, os, sys, time
from datetime import datetime, date, timedelta
from pathlib import Path

# Retrieve ViewState, session and other codes and info from request to:
main_url = "http://www2.pch.etat.lu/comptage/home.jsf"
# Use it to fulfill request to target url at:
data_url = "http://www2.pch.etat.lu/comptage/poste_detail.jsf"

lvl3_headers = {
    'Host': 'www2.pch.etat.lu',
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:106.0) Gecko/20100101 Firefox/106.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-CA,en-US;q=0.7,en;q=0.3',
    'Accept-Encoding': 'gzip, deflate',
    'Referer': 'http://www2.pch.etat.lu/comptage/chart_journalier.jsf',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Origin': 'http://www2.pch.etat.lu',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Cookie': 'JSESSIONID=yCJmU61OXqn5Qnh-y8AFWivvC5twbmunD6vzmNtE.wwwsrv; _pk_id.22.b80c=53b2d0142cbaea28.1669379308.1.1669379308.1669379308.; _pk_ses.22.b80c=1',
    'Upgrade-Insecure-Requests': '1'
}
s = requests.Session()
s.headers.update(lvl3_headers)

lvl3_data_pckg = {
        "j_idt21": "j_idt21",
        "j_idt21:j_idt23": "chart_journalier",
        "j_idt21:j_idt26": "U",
        "j_idt21:dateDuInputDate": "02.01.2022",
        "j_idt21:dateDuInputCurrentDate": "01/2022",
        "j_idt21:dateAuInputDate": "02.01.2022",
        "j_idt21:dateAuInputCurrentDate": "08/2022",
        "j_idt21:direction": "1",
        "j_idt21:j_idt35": "Afficher",
        "javax.faces.ViewState": '-6887193091565512890:2496882381702850699'
    }
lvl3_res = s.post(data_url + ';jsessionid=' + '', data=lvl3_data_pckg)

if lvl3_res.ok:
    #print(lvl3_res.text)
    soup = BeautifulSoup(lvl3_res.text, 'html.parser')
    tr = soup.find("table", class_="tablepch").find_all("tr")
    cars = [x.text for x in tr[3].find_all("td")] + [x.text for x in tr[9].find_all("td")]
    print(cars)
else:
    print(lvl3_res.text)
