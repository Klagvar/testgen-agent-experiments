import json, urllib.request

d = json.loads(urllib.request.urlopen('https://openrouter.ai/api/v1/models').read())['data']
for m in d:
    if 'haiku' in m['id'].lower():
        p = m.get('pricing', {})
        pp = float(p.get('prompt', 0)) * 1e6
        pc = float(p.get('completion', 0)) * 1e6
        if pp > 0:
            print(f"{m['id']:55s}  in={pp:.2f}  out={pc:.2f}")
