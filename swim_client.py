import socket


class SwimClient:

    def __init__(
        self,
        host="localhost",
        port=4242
    ):
        self.host = host
        self.port = port
        self.socket = None


    def connect(self):

        print(
            f"Connecting to SWIM at "
            f"{self.host}:{self.port}..."
        )

        self.socket = socket.create_connection(
            (self.host, self.port),
            timeout=10
        )

        print("Connected to real SWIM.")


    def close(self):

        if self.socket is not None:

            self.socket.close()

            self.socket = None

            print("SWIM connection closed.")


    def send_command(self, command):

        if self.socket is None:
            raise RuntimeError(
                "Not connected to SWIM."
            )

        message = command + "\n"

        self.socket.sendall(
            message.encode("utf-8")
        )

        reply = self.socket.recv(
            1024
        ).decode("utf-8").strip()

        if reply.startswith("error:"):
            raise RuntimeError(reply)

        return reply


    # ========================================================
    # MONITORING / PROBES
    # ========================================================

    def get_dimmer(self):

        return float(
            self.send_command(
                "get_dimmer"
            )
        )


    def get_servers(self):

        return int(
            self.send_command(
                "get_servers"
            )
        )


    def get_active_servers(self):

        return int(
            self.send_command(
                "get_active_servers"
            )
        )


    def get_max_servers(self):

        return int(
            self.send_command(
                "get_max_servers"
            )
        )


    def get_utilization(self, server_id):

        return float(
            self.send_command(
                f"get_utilization server{server_id}"
            )
        )


    def get_basic_response_time(self):

        return float(
            self.send_command(
                "get_basic_rt"
            )
        )


    def get_optional_response_time(self):

        return float(
            self.send_command(
                "get_opt_rt"
            )
        )


    def get_basic_throughput(self):

        return float(
            self.send_command(
                "get_basic_throughput"
            )
        )


    def get_optional_throughput(self):

        return float(
            self.send_command(
                "get_opt_throughput"
            )
        )


    def get_arrival_rate(self):

        return float(
            self.send_command(
                "get_arrival_rate"
            )
        )


    # ========================================================
    # EXECUTION / EFFECTORS
    # ========================================================

    def add_server(self):

        return self.send_command(
            "add_server"
        )


    def remove_server(self):

        return self.send_command(
            "remove_server"
        )


    def set_dimmer(self, value):

        return self.send_command(
            f"set_dimmer {value}"
        )


# ============================================================
# SIMPLE CONNECTION TEST
# ============================================================

if __name__ == "__main__":

    client = SwimClient()

    try:

        client.connect()

        print("\n=== REAL SWIM TEST ===")

        active_servers = (
            client.get_active_servers()
        )

        max_servers = (
            client.get_max_servers()
        )

        dimmer = (
            client.get_dimmer()
        )

        print(
            f"Active Servers: "
            f"{active_servers}"
        )

        print(
            f"Maximum Servers: "
            f"{max_servers}"
        )

        print(
            f"Dimmer: "
            f"{dimmer}"
        )

    finally:

        client.close()
