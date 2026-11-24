import json
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch
from pathlib import Path
from bean.runtime.retained_lab import RetainedLab, validate_weighted_mean

class RetainedLabTests(unittest.TestCase):
    def test_invalid(self):
        for args in ({"values":[],"weights":[]},{"values":[1],"weights":[0]},
                     {"values":[True],"weights":[1]},{"values":[2],"weights":[-1]}):
            with self.assertRaises(ValueError): validate_weighted_mean(args)
    def test_unsupported_socket_transport(self):
        with patch("bean.runtime.retained_lab.socket") as transport:
            del transport.AF_UNIX
            with self.assertRaisesRegex(NotImplementedError, "requires AF_UNIX"):
                RetainedLab("worker.sock").weighted_mean({"values":[3,8],"weights":[3,1]})
            transport.socket.assert_not_called()

    def test_socket_protocol(self):
        args = {"values":[3,8],"weights":[3,1]}
        with patch("bean.runtime.retained_lab.socket") as transport:
            transport.AF_UNIX = 1
            transport.SOCK_STREAM = 2
            peer = transport.socket.return_value.__enter__.return_value
            stream = peer.makefile.return_value.__enter__.return_value
            stream.readline.return_value = json.dumps({"status":"ok","value":4.25,"source_sha256":"a"*64}).encode()+b"\n"
            result = RetainedLab("worker.sock").weighted_mean(args)
            transport.socket.assert_called_once_with(1, 2)
            peer.connect.assert_called_once_with("worker.sock")
            peer.settimeout.assert_called_once_with(12)
            request = peer.sendall.call_args.args[0]
            self.assertTrue(request.endswith(b"\n"))
            self.assertEqual(json.loads(request), {"skill":"weighted_mean", **args})
            self.assertEqual(result["value"], 4.25)
            self.assertEqual(result["source_sha256"], "a"*64)
            self.assertFalse(result["independent_correctness_verified"])
            stream.readline.return_value = b'{"status":"ok","value":4.25,"source_sha256":"bad"}\n'
            with self.assertRaisesRegex(ValueError, "missing source digest"):
                RetainedLab("worker.sock").weighted_mean(args)

    @unittest.skipUnless(hasattr(socket, "AF_UNIX"), "interprocess Unix socket transport unavailable")
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
