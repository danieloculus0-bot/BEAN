import json
import socket
import tempfile
import threading
import unittest
from pathlib import Path
from bean.runtime.retained_lab import RetainedLab, validate_weighted_mean

class RetainedLabTests(unittest.TestCase):
    def test_invalid(self):
        for args in ({"values":[],"weights":[]},{"values":[1],"weights":[0]},
                     {"values":[True],"weights":[1]},{"values":[2],"weights":[-1]}):
            with self.assertRaises(ValueError): validate_weighted_mean(args)
    def test_socket_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=str(Path(tmp)/"worker.sock")
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as server:
                server.bind(path)
                server.listen(1)
                def serve():
                    with server.accept()[0] as client:
                        req=json.loads(client.makefile("rb").readline())
                        assert req["skill"]=="weighted_mean"
                        client.sendall(json.dumps({"status":"ok","value":4.25,"source_sha256":"a"*64}).encode()+b"\n")
                thread=threading.Thread(target=serve)
                thread.start()
                result=RetainedLab(path).weighted_mean({"values":[3,8],"weights":[3,1]})
                thread.join(5)
                self.assertEqual(result["value"],4.25)
                self.assertEqual(result["source_sha256"],"a"*64)
                self.assertFalse(result["independent_correctness_verified"])
