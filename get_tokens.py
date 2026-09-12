import urllib.request
import json
import os

url = 'https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json'
print('Downloading Angel One instrument master...')
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=40) as resp:
    instruments = json.loads(resp.read().decode('utf-8'))

print('Total instruments in master:', len(instruments))

tokens = {}
for item in instruments:
    if item.get('exch_seg') == 'NSE' and item.get('symbol', '').endswith('-EQ'):
        sym = item.get('symbol', '').replace('-EQ', '').upper()
        tokens[sym] = item.get('token')

out_file = os.path.join('data', 'angel_tokens.json')
os.makedirs('data', exist_ok=True)
with open(out_file, 'w', encoding='utf-8') as f:
    json.dump(tokens, f, indent=2)

print(f'Successfully wrote {len(tokens)} NSE equity tokens to {out_file}!')

needed = ['IDFCFIRSTB', 'PNB', 'BEL', 'TATAPOWER', 'SUZLON', 'IRFC', 'JIOFIN', 'FEDERALBNK', 'BHEL', 'PFC', 'RECLTD', 'CANBK', 'NATIONALUM', 'ASHOKLEY']
for n in needed:
    print(f'{n}: {tokens.get(n)}')
