from fastmcp import FastMCP
from netmiko import ConnectHandler
import os
from dotenv import load_dotenv
load_dotenv()

# ----------------------------
# MCP server
# ----------------------------
mcp = FastMCP("netmiko-network-tools")

# ----------------------------
# Device connection helper
# ----------------------------
def connect_device(ip: str, device_type: str = "cisco_ios"):
    return ConnectHandler(
        device_type=device_type,
        host=ip,
        username=os.getenv("NET_USERNAME"),
        password=os.getenv("NET_PASSWORD"),
        fast_cli=True
    )

# ----------------------------
# Core Python functions 
# ----------------------------
def _show_version(ip: str, device_type: str = "cisco_ios") -> dict:
    """Run 'show version'"""
    try:
        conn = connect_device(ip, device_type)
        output = conn.send_command("show version")
        conn.disconnect()
        return {"ip": ip, "command": "show version", "output": output}
    except Exception as e:
        return {"error": str(e)}

def _show_interfaces(ip: str, device_type: str = "cisco_ios") -> dict:
    """Run 'show ip interface brief'"""
    try:
        conn = connect_device(ip, device_type)
        output = conn.send_command("show ip interface brief")
        conn.disconnect()
        return {"ip": ip, "command": "show ip interface brief", "output": output}
    except Exception as e:
        return {"error": str(e)}

def _check_reachability(ip: str, device_type: str = "cisco_ios") -> dict:
    """Simple reachability check"""
    try:
        conn = connect_device(ip, device_type)
        conn.disconnect()
        return {"ip": ip, "reachable": True}
    except Exception:
        return {"ip": ip, "reachable": False}

def _show_route_table(ip: str, device_type: str = "cisco_ios") -> dict:
    """Run 'show ip route'"""
    try:
        conn = connect_device(ip, device_type)
        output = conn.send_command("show ip route")
        conn.disconnect()
        return {"ip": ip, "command": "show ip route", "output": output}
    except Exception as e:
        return {"error": str(e)}   

# ----------------------------
# Wrap functions for MCP server with clean tool names
# ----------------------------
mcp.tool(name="show_version")(_show_version)
mcp.tool(name="show_interfaces")(_show_interfaces)
mcp.tool(name="check_reachability")(_check_reachability)
mcp.tool(name="show_route_table")(_show_route_table)

# ----------------------------
# Run MCP server 
# ----------------------------
if __name__ == "__main__":

    print("Starting MCP server 'netmiko-network-tools' (stdio transport)...")
    mcp.run()
