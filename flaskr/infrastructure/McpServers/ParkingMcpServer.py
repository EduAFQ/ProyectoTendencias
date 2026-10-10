from fastmcp import FastMCP

from flaskr import create_app
from flaskr.services.parkingServices import ParkingServices

mcp = FastMCP("Parking MCP Server")
aplicacion = create_app()
servicio = ParkingServices(aplicacion.extensions["parking_repository"])


@mcp.tool(description="Saluda a una persona.")
def greet(name: str) -> str:
    return f"Hello, {name}!"


@mcp.tool(description="Lista las plazas de parqueadero, solo las disponibles.")
def mcp_listar_plazas(disponibles: bool = False):
    return servicio.listar_plazas(disponibles)



if __name__ == "__main__":
    mcp.run()