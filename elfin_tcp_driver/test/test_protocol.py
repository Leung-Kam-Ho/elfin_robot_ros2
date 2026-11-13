import socketserver
import threading
import unittest

from elfin_tcp_driver.protocol import (
    HansRobotTcpClient,
    ProtocolError,
    format_robotiq_command,
    format_robot_speed_override,
    parse_robotiq_moving,
)


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

    def test_formats_robotiq_position_command(self):
        self.assertEqual(
            format_robotiq_command(70, 250, 10),
            "SetRobotiq,70,250,10,;",
        )
        self.assertEqual(
            format_robotiq_command(70, 100, 25),
            "SetRobotiq,70,100,25,;",
        )
        self.assertEqual(
            format_robotiq_command(-5, 400, 5),
            "SetRobotiq,0,250,10,;",
        )

    def test_formats_robot_speed_override(self):
        self.assertEqual(
            format_robot_speed_override(0, 25),
            "SetOverride,0,0.2500,;",
        )
        with self.assertRaisesRegex(ValueError, "1 and 100"):
            format_robot_speed_override(0, 0)

    def test_robotiq_position_and_status_responses(self):
        self.assertTrue(parse_robotiq_moving(["0", "3", "1", "1"]))
        self.assertFalse(parse_robotiq_moving(["3", "3", "1", "1"]))
        self.assertFalse(parse_robotiq_moving(["2", "3", "1", "1"]))

    def test_rejects_invalid_robotiq_state(self):
        with self.assertRaisesRegex(ValueError, "finite"):
            format_robotiq_command(float("nan"))
        with self.assertRaisesRegex(ProtocolError, "Unexpected RobotiqStatus"):
            parse_robotiq_moving(["9", "9", "9", "9"])


if __name__ == "__main__":
    unittest.main()
