import socketserver
import threading
import unittest

from elfin_tcp_driver.protocol import HansRobotTcpClient, ProtocolError


class _ProtocolHandler(socketserver.StreamRequestHandler):
    def handle(self):
        while True:
            command = bytearray()
            while not command.endswith(b";"):
                char = self.rfile.read(1)
                if not char:
                    return
                command.extend(char)

            if command == b"ReadDCSStatus,;":
                self.wfile.write(b"ReadDCSStatus,OK,10,;")
            elif command == b"BadCommand,;":
                self.wfile.write(b"BadCommand,Fail,1010,;")
            else:
                self.wfile.write(b"Unknown,OK,;")
            self.wfile.flush()


class TcpProtocolTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), _ProtocolHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join()

    def setUp(self):
        self.client = HansRobotTcpClient(
            "127.0.0.1", self.server.server_address[1], response_timeout=1.0
        )

    def tearDown(self):
        self.client.close()

    def test_reads_one_complete_reply_and_reuses_connection(self):
        self.assertEqual(self.client.request("ReadDCSStatus,;"), ["10"])
        self.assertEqual(self.client.request("ReadDCSStatus,;"), ["10"])

    def test_robot_failure_reply_raises_protocol_error(self):
        with self.assertRaisesRegex(ProtocolError, "1010"):
            self.client.request("BadCommand,;")


if __name__ == "__main__":
    unittest.main()
