from swim_client import SwimClient


def read_server_utilizations(
    client,
    active_servers,
    max_servers
):

    """
    Read utilization information from SWIM.

    Important SWIM behavior:
    A newly added server does not appear in the
    utilization map until it has actually emitted
    a busy=true signal.

    Therefore, a missing utilization entry for an
    active server is treated as zero utilization
    for the current monitoring snapshot.
    """

    utilization_values = []

    available_entries = 0

    for server_id in range(
        1,
        max_servers + 1
    ):

        try:

            utilization = (
                client.get_utilization(
                    server_id
                )
            )

            utilization_values.append(
                utilization
            )

            available_entries += 1

        except RuntimeError as error:

            # SWIM returns this when the utilization
            # map does not yet contain the server.
            if "does no exist" in str(error):

                continue

            # Any other error should still be exposed.
            raise

    # Sum only actual SWIM utilization observations.
    total_utilization = sum(
        utilization_values
    )

    # Missing active-server entries represent servers
    # that have not yet recorded busy work, so their
    # utilization contribution is zero.
    if active_servers > 0:

        average_utilization = (
            total_utilization
            / active_servers
        )

    else:

        average_utilization = 0.0

    return (
        average_utilization,
        total_utilization,
        available_entries
    )


def monitor():

    print("=== MONITOR — REAL SWIM ===")

    client = SwimClient()

    try:

        client.connect()

        # ====================================================
        # BASIC SWIM STATE
        # ====================================================

        servers = (
            client.get_servers()
        )

        active_servers = (
            client.get_active_servers()
        )

        max_servers = (
            client.get_max_servers()
        )

        server_booting = (
            servers > active_servers
        )

        dimmer = (
            client.get_dimmer()
        )

        arrival_rate = (
            client.get_arrival_rate()
        )

        # ====================================================
        # RESPONSE-TIME MEASUREMENTS
        # ====================================================

        basic_rt = (
            client.get_basic_response_time()
        )

        optional_rt = (
            client.get_optional_response_time()
        )

        basic_throughput = (
            client.get_basic_throughput()
        )

        optional_throughput = (
            client.get_optional_throughput()
        )

        total_throughput = (
            basic_throughput
            + optional_throughput
        )

        if total_throughput > 0:

            response_time = (
                (
                    basic_throughput
                    * basic_rt
                )
                +
                (
                    optional_throughput
                    * optional_rt
                )
            ) / total_throughput

        else:

            response_time = 0.0

        # ====================================================
        # UTILIZATION
        # ====================================================

        (
            average_utilization,
            total_utilization,
            utilization_entries
        ) = read_server_utilizations(
            client,
            active_servers,
            max_servers
        )

        # ====================================================
        # COMPLETE RUNTIME STATE
        # ====================================================

        state = {

            "response_time":
                response_time,

            "servers":
                servers,

            "active_servers":
                active_servers,

            "max_servers":
                max_servers,

            "server_booting":
                server_booting,

            "utilization":
                average_utilization,

            "total_utilization":
                total_utilization,

            "utilization_entries":
                utilization_entries,

            "dimmer":
                dimmer,

            "arrival_rate":
                arrival_rate,

            "basic_response_time":
                basic_rt,

            "optional_response_time":
                optional_rt,

            "basic_throughput":
                basic_throughput,

            "optional_throughput":
                optional_throughput
        }

        # ====================================================
        # DISPLAY
        # ====================================================

        print(
            f"Observed Total Servers: "
            f"{servers}"
        )

        print(
            f"Observed Active Servers: "
            f"{active_servers}"
        )

        print(
            f"Observed Maximum Servers: "
            f"{max_servers}"
        )

        print(
            f"Server Booting: "
            f"{server_booting}"
        )

        print(
            f"Observed Response Time: "
            f"{response_time:.4f} seconds"
        )

        print(
            f"Observed Average Utilization: "
            f"{average_utilization * 100:.1f}%"
        )

        print(
            f"Observed Total Utilization: "
            f"{total_utilization:.3f}"
        )

        print(
            f"Utilization Entries Available: "
            f"{utilization_entries} / "
            f"{active_servers} active server(s)"
        )

        print(
            f"Observed Dimmer: "
            f"{dimmer}"
        )

        print(
            f"Observed Arrival Rate: "
            f"{arrival_rate}"
        )

        print(
            f"Basic Response Time: "
            f"{basic_rt:.4f} seconds"
        )

        print(
            f"Optional Response Time: "
            f"{optional_rt:.4f} seconds"
        )

        return state

    finally:

        client.close()


if __name__ == "__main__":

    monitor()
