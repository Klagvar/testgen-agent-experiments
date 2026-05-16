import json, sys, urllib.request

model = sys.argv[1] if len(sys.argv) > 1 else 'anthropic/claude-haiku-4.5'
url = f'https://openrouter.ai/api/v1/models/{model}/endpoints'
d = json.loads(urllib.request.urlopen(url).read())['data']
print(f"Model: {d['id']}")
print(f"Endpoints: {len(d['endpoints'])}")
for e in d['endpoints']:
    name = e.get('name', e.get('provider_name', '?'))
    slug = e.get('tag') or e.get('provider_name') or '?'
    pp = float(e.get('pricing', {}).get('prompt', 0)) * 1e6
    pc = float(e.get('completion', {}).get('prompt', 0)) * 1e6 if 'completion' in e and isinstance(e.get('completion'), dict) else float(e.get('pricing', {}).get('completion', 0)) * 1e6
    uptime = e.get('uptime_last_30m', '?')
    print(f"  name='{name}'  slug='{slug}'  in={pp:.2f}/M  out={pc:.2f}/M  uptime={uptime}")
