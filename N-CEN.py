import requests
import json
from bs4 import BeautifulSoup
import pandas as pd
from dateutil.relativedelta import relativedelta
import xmltodict


CIK_List = ['0001678124', '0001803498', '0001842754', '0001736035', '0001061630']

def recursive_items(d):
    items = []
    for key, value in d.items():
        if isinstance(value, dict):
            items.extend(recursive_items(value))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    items.extend(recursive_items(item))
                else:
                    items.append({key: item})  # Handle lists directly nested under keys
        else:
            items.append({key: value})
    return items

rows = []
for cik in CIK_List:
    header = {
        'Accept':'*/*',
        'Accept-Encoding':'gzip, deflate, br, zstd',
        'Accept-Language':'en-US,en;q=0.9',
        'Cache-Control':'no-cache',
        'Origin':'https://www.sec.gov',
        'Pragma':'no-cache',
        'Priority':'u=1, i',
        'Referer':'https://www.sec.gov/',
        'Sec-Ch-Ua':'"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
        'Sec-Ch-Ua-Mobile':'?0',
        'Sec-Ch-Ua-Platform':'"Windows"',
        'Sec-Fetch-Dest':'empty',
        'Sec-Fetch-Mode':'cors',
        'Sec-Fetch-Site':'same-site',
        'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
    }
    resp = requests.get(f'https://data.sec.gov/submissions/CIK{cik}.json', headers=header)
    filings_data = resp.json()['filings']['recent']
    df = pd.DataFrame()
    for key, value in filings_data.items():
        df[key]=value
    df = df[df['form'] == 'N-CEN']
    df = df[df['filingDate'] >= '2019-01-01'] # Filtering the dataFrame for date grater than 2019-01-01
    for file in json.loads(df.to_json(orient='records')):
        accessionNumber = file['accessionNumber'].replace('-','')
        accessionNumber2 = file['accessionNumber']
        header = {
            'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding':'gzip, deflate, br, zstd',
            'Accept-Language':'en-US,en;q=0.9',
            'Cache-Control':'max-age=0',
            'Priority':'u=0, i',
            'Sec-Ch-Ua':'"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
            'Sec-Ch-Ua-Mobile':'?0',
            'Sec-Ch-Ua-Platform':'"Windows"',
            'Sec-Fetch-Dest':'document',
            'Sec-Fetch-Mode':'navigate',
            'Sec-Fetch-Site':'same-origin',
            'Sec-Fetch-User':'?1',
            'Upgrade-Insecure-Requests':'1',
            'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
        }
        resp2 = requests.get(f'https://www.sec.gov/Archives/edgar/data/{cik[3:]}/{accessionNumber}/{accessionNumber2}.txt',headers=header)
        soup = BeautifulSoup(resp2.content, 'lxml')
        data_dict = xmltodict.parse(str(soup.find('formdata')), dict_constructor=dict)
        results = recursive_items(data_dict)
        for result in results:
            for key, value in result.items():
                if value == 'N/A':
                    result[key] = ''
                if 'registrantfullname' in key:
                    shortName = value
                elif '@reportendingperiod' in key:
                    EndDate = value
                    Period = value
                    RefYear = value.split('-')[0]
        for result in results:
            for key, value in result.items():
                row = {}
                row['CIK'] = cik
                row['shortNam'] = shortName
                row['EndDate'] = EndDate
                row['RefYear'] = RefYear
                row['Period'] = Period
                row['PeriodFP'] = 'FY'
                row['Field'] = key
                row['Value'] = value
                rows.append(row)
                print(row)
df = pd.DataFrame(rows)
df = df.drop_duplicates(subset=["CIK", "shortNam", "EndDate","RefYear", "Period", "PeriodFP", "Field", "Value"])

df.to_excel('N-CEN filing data.xlsx', index=False)

pivot_df = df.pivot_table(index=['CIK', 'Field'], columns='EndDate', values='Value', aggfunc='first')
pivot_df.reset_index()
pivot_df.columns.name = None
pivot_df.reset_index(drop=False, inplace=True)
pivot_df.index = pivot_df.index + 1

pivot_df.to_excel('N-CEN pivot table data.xlsx', index=False)