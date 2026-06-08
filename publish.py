#!/usr/bin/env python3
"""
Publicador de Stories no Instagram (Arena Gourmet) via Graph API (usa curl).
Uso:
  python3 publish.py test <video_url>     # publica 1 story (validacao)
  python3 publish.py run                   # publica os stories devidos AGORA (cron)
  python3 publish.py next                   # mostra a grade (nao posta)

Token: env IG_TOKEN (preferido, p/ GitHub Actions) ou ~/.arena-tools/ig-scheduler/.token.
IG_ID: env ou schedule.json.
"""
import os, sys, json, time, subprocess
from datetime import datetime, timezone, timedelta

GRAPH = "https://graph.facebook.com/v21.0"
HERE = os.path.dirname(os.path.abspath(__file__))
SP_TZ = timezone(timedelta(hours=-3))  # America/Sao_Paulo
DOW = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

def load_cfg(): return json.load(open(os.path.join(HERE, "schedule.json")))

def get_token():
    t = os.environ.get("IG_TOKEN")
    if t: return t.strip()
    p = os.path.join(HERE, ".token")
    if os.path.exists(p): return open(p).read().strip()
    raise SystemExit("Sem token: defina IG_TOKEN ou crie .token")

def _run(args):
    r = subprocess.run(["curl", "-s", "--max-time", "90"] + args, capture_output=True, text=True)
    try: d = json.loads(r.stdout)
    except Exception: raise RuntimeError(f"resposta nao-JSON: {r.stdout[:300]} | {r.stderr[:150]}")
    if isinstance(d, dict) and d.get("error"):
        raise RuntimeError(f"API erro: {d['error'].get('message')} (code {d['error'].get('code')})")
    return d

def _get(url): return _run([url])
def _post(url, data):
    args = [url]
    for k, v in data.items(): args += ["--data-urlencode", f"{k}={v}"]
    return _run(args)

def publish_story(ig_id, token, video_url):
    c = _post(f"{GRAPH}/{ig_id}/media",
              {"media_type": "STORIES", "video_url": video_url, "access_token": token})
    cid = c["id"]
    for _ in range(40):
        st = _get(f"{GRAPH}/{cid}?fields=status_code&access_token={token}")
        sc = st.get("status_code")
        if sc == "FINISHED": break
        if sc == "ERROR": raise RuntimeError(f"container ERROR: {st}")
        time.sleep(5)
    else:
        raise TimeoutError("container nao ficou pronto")
    return _post(f"{GRAPH}/{ig_id}/media_publish", {"creation_id": cid, "access_token": token}).get("id")

def url_for(cfg, it): return it.get("url") or f"{cfg['base_url']}/{it['name']}.mp4"
def _sp(): return os.path.join(HERE, "posted-log.json")
def _load(): return json.load(open(_sp())) if os.path.exists(_sp()) else {}
def _save(s): json.dump(s, open(_sp(), "w"), indent=2)

def cmd_next(cfg):
    now = datetime.now(SP_TZ); print(f"Agora (SP): {now:%a %H:%M}\nGrade:")
    for it in cfg["schedule"]: print(f"  {it['dow']} {it['time']}  {it['name']}")

def cmd_run(cfg, window=12):
    token = get_token(); ig_id = os.environ.get("IG_ID") or cfg["ig_id"]
    now = datetime.now(SP_TZ); today = DOW[now.weekday()]; key_day = now.strftime("%Y-%m-%d")
    state = _load(); done = set(state.get(key_day, [])); posted = []
    for it in cfg["schedule"]:
        if it["dow"] != today: continue
        hh, mm = map(int, it["time"].split(":"))
        sched = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        key = f"{it['time']}-{it['name']}"
        if abs((now - sched).total_seconds())/60 <= window and key not in done:
            try:
                pid = publish_story(ig_id, token, url_for(cfg, it))
                print(f"OK {it['name']} -> {pid}"); done.add(key); posted.append(it['name'])
            except Exception as e: print(f"ERRO {it['name']}: {e}", file=sys.stderr)
    if posted: state[key_day] = sorted(done); _save(state)
    else: print("nada devido nesta janela.")

def cmd_test(cfg, url):
    token = get_token(); ig_id = os.environ.get("IG_ID") or cfg["ig_id"]
    print(f"Publicando teste em IG {ig_id}:\n  {url}")
    print(f"OK! story id = {publish_story(ig_id, token, url)}")

if __name__ == "__main__":
    cfg = load_cfg(); cmd = sys.argv[1] if len(sys.argv) > 1 else "next"
    if cmd == "test": cmd_test(cfg, sys.argv[2])
    elif cmd == "run": cmd_run(cfg)
    else: cmd_next(cfg)
