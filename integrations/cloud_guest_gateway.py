"""Guest-facing BEAN gateway. Uses existing Core solver and reasoning journal.
Run as a separate unprivileged account with a dedicated guest storage root.
Bind loopback only; HTTPS reverse proxy required for public access.
"""
from __future__ import annotations
import json, os, re, secrets, threading, time, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from bean.learning.reasoning_service import NativeReasoningService
from bean.reasoning.local_llamacpp_provider import LocalLlamaCppProvider
from bean.engineering.spaceflight import solve_spaceflight_reference

ROOT=Path(os.environ.get("BEAN_GUEST_ROOT","/var/lib/bean-web/guests"))
ORIGIN="https://danieloculus0-bot.github.io"
MODEL=os.environ.get("BEAN_LOCAL_LLM_MODEL","qwen2.5:7b")
BASE=os.environ.get("BEAN_LOCAL_LLM_URL","http://127.0.0.1:11434")
LOCK=threading.Lock()
QUOTA_LOCK=threading.Lock()
RATE={}
MAX_SESSIONS=128

def guest(token):
    if not isinstance(token,str) or not re.fullmatch(r"[0-9a-f]{64}",token):
        raise ValueError("Invalid guest token")
    path=ROOT/token
    if not path.is_dir(): raise ValueError("Guest session not found")
    return path

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def reply(self,status,body):
        raw=json.dumps(body,ensure_ascii=False,allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(raw)))
        self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        if self.headers.get("Origin")==ORIGIN:
            self.send_header("Access-Control-Allow-Origin",ORIGIN)
            self.send_header("Vary","Origin")
        self.end_headers()
        self.wfile.write(raw)
    def do_OPTIONS(self):
        self.send_response(204)
        if self.headers.get("Origin")==ORIGIN:
            self.send_header("Access-Control-Allow-Origin",ORIGIN)
            self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS")
            self.send_header("Access-Control-Allow-Headers","Content-Type")
            self.send_header("Vary","Origin")
        self.end_headers()
    def do_GET(self):
        if urlsplit(self.path).path!="/api/health":
            return self.reply(404,{"error":"not found"})
        from urllib.request import urlopen
        ready=False
        try:
            with urlopen(BASE+"/api/tags",timeout=3) as r:
                ready=any(x.get("name")==MODEL for x in json.load(r).get("models",[]))
        except Exception: pass
        self.reply(200,{"service":"BEAN guest Core","native_solver":True,"model_present":ready,"model":MODEL,"memory":"isolated guest SHA journal","production_memory_exposed":False})
    def do_POST(self):
        route=urlsplit(self.path).path
        if route not in ("/api/session","/api/chat","/api/orbit"):
            return self.reply(404,{"error":"not found"})
        try:
            size=int(self.headers.get("Content-Length","0"))
            if not 0<size<=8192: raise ValueError("Request size invalid")
            data=json.loads(self.rfile.read(size))
            if not isinstance(data,dict): raise ValueError("Expected object")
        except (ValueError,TypeError): return self.reply(400,{"error":"Invalid request"})
        # Proxy is the only network ingress. Bound total guest requests as well as concurrency.
        now=time.monotonic()
        with QUOTA_LOCK:
            RATE["all"]=[x for x in RATE.get("all",[]) if now-x<60]
            if len(RATE["all"])>=24: return self.reply(429,{"error":"Server capacity reached; retry later"})
            RATE["all"].append(now)
        if route=="/api/session":
            with QUOTA_LOCK:
                if len(list(ROOT.iterdir()))>=MAX_SESSIONS:
                    return self.reply(503,{"error":"Guest session capacity reached"})
                token=secrets.token_hex(32)
                (ROOT/token).mkdir(mode=0o700)
            return self.reply(201,{"token":token})
        if route=="/api/orbit":
            try:
                result=solve_spaceflight_reference({"schema":"bean.spaceflight_request.v1","calculation":"orbit","parameters":{"body":data.get("body"),"altitude_km":data.get("altitude_km")}})
                return self.reply(200,result)
            except (ValueError,TypeError,OverflowError):
                return self.reply(400,{"error":"Invalid orbit parameters"})
        try:
            path=guest(data.get("token"))
            message=data.get("message")
            if not isinstance(message,str) or not 1<=len(message.strip())<=1200:
                raise ValueError("Message must contain 1–1200 characters")
        except ValueError as e: return self.reply(400,{"error":str(e)})
        if not LOCK.acquire(blocking=False):
            return self.reply(429,{"error":"Inference busy; retry later"})
        core=None
        try:
            provider=LocalLlamaCppProvider(base_url=BASE,model_name=MODEL,timeout_seconds=180,max_tokens=256)
            core=NativeReasoningService(path/"reasoning.sqlite",model=provider)
            events=core.bank.journal.events()
            if len(events)>=100: return self.reply(429,{"error":"Guest journal limit reached"})
            recent=[{"question":r["data"].get("query","")[-450:],"answer":r["data"].get("answer","")[:450]} for r in events if r.get("kind")=="inference" and isinstance(r["data"].get("answer"),str)][-2:]
            query=("Previous guest exchanges, unverified: "+json.dumps(recent,ensure_ascii=False)+"\nCurrent question: "+message)[:3000]
            result=core.reason(domain="guest-conversation",task_ref="guest:"+uuid.uuid4().hex,query=query)
            return self.reply(200,{"answer":result["answer"],"receipt_id":result["receipt_id"],"model":result["model_id"],"provider":result["provider_kind"],"verified_outcome":False,"memory":"isolated guest journal"})
        except Exception:
            return self.reply(503,{"error":"BEAN inference unavailable; no response fabricated"})
        finally:
            if core: core.close()
            LOCK.release()

if __name__=="__main__":
    ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
    ThreadingHTTPServer(("127.0.0.1",8765),Handler).serve_forever()
