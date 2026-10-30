import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    # Start the MCP server as a subprocess
    server_params = StdioServerParameters(
        command="python",
        args=["network_mcp_server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:

            # Required handshake
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            print("\nAvailable MCP tools:")
            for tool in tools.tools:
                print(f"- {tool.name}")

            ip = "172.16.10.1"

            # ----------------------------
            # check_reachability
            # ----------------------------
            print("\n== check_reachability ==")
            result = await session.call_tool(
                "check_reachability",
                {
                    "ip": ip,
                    "device_type": "cisco_ios"
                }
            )
            print(result.content[0].text)

            # ----------------------------
            # show_version
            # ----------------------------
            print("\n== show_version ==")
            result = await session.call_tool(
                "show_version",
                {
                    "ip": ip,
                    "device_type": "cisco_ios"
                }
            )
            print(result.content[0].text)

            # ----------------------------
            # show_interfaces
            # ----------------------------
            print("\n== show_interfaces ==")
            result = await session.call_tool(
                "show_interfaces",
                {
                    "ip": ip,
                    "device_type": "cisco_ios"
                }
            )
            print(result.content[0].text)

            # ----------------------------
            # show_routing_table
            # ----------------------------
            print("\n== show_routing_table ==")
            result = await session.call_tool(
                "show_routing_table",
                {
                    "ip": ip,
                    "device_type": "cisco_ios"
                }
            )
            print(result.content[0].text)

if __name__ == "__main__":
    asyncio.run(main())
