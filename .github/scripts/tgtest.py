# tgtest.py - naye ArthaSaar bot ka token + members test.
# Token kabhi print nahi hota. 403 = usne abhi /start nahi kiya.
import json, os, urllib.request

tok = os.environ.get('TG_TOKEN', '')

def api(method, data):
    url = 'https://api.telegram.org/bot' + tok + '/' + method
    req = urllib.request.Request(url, data=json.dumps(data).encode(),
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode())
        except Exception:
            return {'ok': False, 'error': str(e)}
    except Exception as e:
        return {'ok': False, 'error': str(e)}

me = api('getMe', {})
if not me.get('ok'):
    print('TOKEN FAIL:', me.get('description') or me.get('error'))
else:
    b = me.get('result', {})
    print('TOKEN OK | bot =', b.get('username'), '| name =', b.get('first_name'))
    members = [1392604324, 1148261593, 1215372010, 1182983939, 1785489570, 1073463083]
    txt = 'ARTHASAAR TEST\n\nNaya bot online ho gaya hai! Ye ek test message hai - ignore karo.'
    for cid in members:
        res = api('sendMessage', {'chat_id': cid, 'text': txt})
        if res.get('ok'):
            print('sent OK:', cid)
        else:
            print('FAILED :', cid, '|', res.get('description') or res.get('error'))
