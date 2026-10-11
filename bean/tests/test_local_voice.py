"""Offline tests: local Ollama, BEAN identity, Windows voice, conversation gates.

No speech drivers, microphone, model, network or physical motors required.
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from bean.voice import chat, ollama, persona, windows_speech


class FakeHttpResponse:
    def __init__(self, data):
        self.data = json.dumps(data).encode("utf-8")
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, *args):
        return self.data


class OllamaLocalTests(unittest.TestCase):
    def test_only_loopback_addresses_permitted(self):
        for url in ("http://127.0.0.1:11434",
                    "http://localhost:11434/",
                    "http://[::1]:11434"):
            with self.subTest(url=url):
                self.assertEqual(ollama.validated_local_url(url),
                                 url.rstrip("/"))
        for url in ("https://localhost:11434",
                    "http://192.168.1.5:11434",
                    "http://evil.example:11434",
                    "http://alice@localhost:11434",
                    "http://127.0.0.1:11434/exfiltrate",
                    "http://127.0.0.1:11434?key=one",
                    "file:///tmp/model", "", "http://127.0.0.1"):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    ollama.validated_local_url(url)

    def test_installed_chat_model_selected_without_embedding(self):
        observed = []
        def fake(request,timeout):
            observed.append(request.full_url)
            return FakeHttpResponse({"models":[
                {"name":"nomic-embed-text:latest"},
                {"name":"small-chat:latest"}]})
        client = ollama.OllamaClient(opener=fake)
        self.assertEqual(client.select_model(), "small-chat:latest")
        self.assertEqual(client.select_model("small-chat:latest"),
                         "small-chat:latest")
        with self.assertRaisesRegex(ollama.OllamaError,"not installed"):
            client.select_model("invented:model")
        self.assertTrue(all(url.endswith("/api/tags") for url in observed))

    def test_model_chat_is_local_and_never_calls_tools(self):
        requests = []
        def fake(request,timeout):
            requests.append(request)
            return FakeHttpResponse({
                "message":{"role":"assistant","content":"Hey, I am BEAN!"}})
        client = ollama.OllamaClient(opener=fake)
        reply = client.chat("small-chat:latest", [
            {"role":"system","content":"BEAN's verified context"},
            {"role":"user","content":"Hello"}])
        self.assertEqual(reply,"Hey, I am BEAN!")
        self.assertEqual(requests[0].full_url,
                         "http://127.0.0.1:11434/api/chat")
        payload = json.loads(requests[0].data)
        self.assertEqual(payload["model"],"small-chat:latest")
        self.assertFalse(payload["stream"])
        self.assertNotIn("tools",payload)
        self.assertEqual(payload["messages"][-1]["content"],"Hello")

    def test_invalid_or_empty_reply_does_not_count_as_conversation(self):
        client = ollama.OllamaClient(
            opener=lambda *_args, **_kw: FakeHttpResponse({"message":{"content":""}}))
        with self.assertRaisesRegex(ollama.OllamaError,"empty"):
            client.chat("model",[{"role":"user","content":"Hi"}])
        client = ollama.OllamaClient(
            opener=lambda *_args, **_kw: FakeHttpResponse({"error":"not loaded"}))
        with self.assertRaisesRegex(ollama.OllamaError,"not loaded"):
            client.chat("model",[{"role":"user","content":"Hi"}])

    def test_without_models_does_not_invent_one(self):
        client = ollama.OllamaClient(
            opener=lambda *_args, **_kw: FakeHttpResponse({"models":[]}))
        with self.assertRaisesRegex(ollama.OllamaError,"No Ollama chat model"):
            client.select_model()


class BeanIdentityAndChatTests(unittest.TestCase):
    def test_fallback_is_actual_bean_declared_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            text, read_db = persona.system_prompt(Path(tmp)/"missing.db")
            self.assertFalse(read_db)
            self.assertIn("supervised",text)
            self.assertIn("LLM",text.lower().replace("llm","LLM"))
            self.assertIn("BEAN",text)
            self.assertIn("cannot execute code",text)
            self.assertIn("without",text)

    def test_existing_brain_metadata_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"bean.db"
            with sqlite3.connect(path) as db:
                db.execute("CREATE TABLE identity "
                           "(id INTEGER, version TEXT, developmental_stage TEXT, "
                           "what_bean_is TEXT, what_bean_is_not TEXT)")
                db.execute("INSERT INTO identity VALUES "
                           "(1,'local-v1','lab','BEAN can evaluate experiments',"
                           "'No claimed sentience')")
                db.execute("CREATE TABLE capabilities (name TEXT,status TEXT)")
                db.execute("INSERT INTO capabilities VALUES ('experiment_evaluation','active')")
                db.commit()
            text, loaded = persona.system_prompt(path)
            self.assertTrue(loaded)
            self.assertIn("local-v1",text)
            self.assertIn("experiment_evaluation",text)
            self.assertNotIn("No local memory DB",text)
            # No inserts or database updates during context retrieval.
            with sqlite3.connect(path) as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM identity").fetchone()[0],1)

    def test_conversation_is_bounded_and_no_false_history_on_failure(self):
        class Local:
            def __init__(self):
                self.requests=[]
                self.fail=False
            def chat(self,model,messages):
                self.requests.append(list(messages))
                if self.fail:
                    raise ollama.OllamaError("provider temporarily unavailable")
                return "reply"
        provider=Local()
        c=chat.BeanConversation(provider,"installed","BEAN system",max_exchanges=2)
        self.assertEqual(c.reply("one"),"reply")
        self.assertEqual(c.reply("two"),"reply")
        self.assertEqual(c.reply("three"),"reply")
        self.assertLessEqual(len(c.turns),4)
        self.assertEqual(c.turns[0]["content"],"two")
        self.assertEqual(provider.requests[-1][0]["role"],"system")
        previous=list(c.turns)
        provider.fail=True
        with self.assertRaises(ollama.OllamaError):
            c.reply("this should not be remembered")
        self.assertEqual(c.turns,previous)
        with self.assertRaises(ValueError):
            c.reply(" ")

    def test_console_typed_messages_and_quit(self):
        fake=SimpleNamespace(reply=lambda text:"hi back")
        source=iter(("Hey BEAN","/quit"))
        output=[]
        chat.run_console(fake,voice=None,read_input=lambda _:next(source),
                         write_output=output.append)
        self.assertTrue(any("BEAN > hi back" in x for x in output))
        self.assertTrue(any("See you soon" in x for x in output))

    def test_console_listens_only_after_explicit_enter(self):
        fake=SimpleNamespace(reply=lambda txt:"Answer to: "+txt)
        class Voice:
            def __init__(self):self.heard=0;self.spoken=[]
            def speak(self,text):self.spoken.append(text)
            def listen(self):
                self.heard+=1
                return "Can you hear me?"
        voice=Voice()
        responses=iter(("", "/quit"))
        captured=[]
        chat.run_console(fake,voice=voice,
                         read_input=lambda _:next(responses),
                         write_output=captured.append)
        self.assertEqual(voice.heard,1)
        self.assertTrue(any("Can you hear me?" in t for t in captured))
        self.assertTrue(any("Answer to" in t for t in voice.spoken))


class WindowsSpeechSafetyTests(unittest.TestCase):
    def test_platform_guard_and_rate_range(self):
        with self.assertRaises(windows_speech.SpeechError):
            windows_speech.WindowsSpeech(platform="linux")
        with self.assertRaises(ValueError):
            windows_speech.WindowsSpeech(platform="win32",rate=11)

    def test_speech_content_passed_on_stdin_not_as_script(self):
        records=[]
        def runner(argv,**kwargs):
            records.append((argv,kwargs))
            return subprocess.CompletedProcess(argv,0,"","")
        s=windows_speech.WindowsSpeech(
            platform="win32",name="Optional voice",rate=2,runner=runner)
        untrusted="' ; Write-Output 'INJECTED' #"
        s.speak(untrusted)
        args,kwargs=records[0]
        self.assertEqual(args[:3],
                         ["powershell.exe","-NoProfile","-NonInteractive"])
        self.assertEqual(kwargs["input"],untrusted)
        self.assertNotIn(untrusted,args[-1])
        self.assertEqual(kwargs["env"]["BEAN_VOICE_RATE"],"2")

    def test_listen_includes_confidence_check_and_transcript(self):
        def runner(argv,**kwargs):
            return subprocess.CompletedProcess(argv,0,"Good morning BEAN","")
        s=windows_speech.WindowsSpeech(platform="win32",runner=runner)
        self.assertEqual(s.listen(),"Good morning BEAN")
        self.assertIn("Confidence",windows_speech.LISTEN_SCRIPT)
        self.assertIn("SetInputToDefaultAudioDevice",windows_speech.LISTEN_SCRIPT)

    def test_windows_speech_failure_does_not_run_commands_from_model(self):
        def runner(argv,**kwargs):
            return subprocess.CompletedProcess(argv,1,"","No speech device")
        s=windows_speech.WindowsSpeech(platform="win32",runner=runner)
        with self.assertRaises(windows_speech.SpeechError):
            s.speak("Hello")


if __name__=="__main__":
    unittest.main()
