"""A local MCP server for testing tool connections without external services."""

from fastmcp import FastMCP

server = FastMCP("Example tools")


@server.tool()
def count_words(text: str) -> int:
	"""Return the number of whitespace-separated words in a string."""
	return len(text.split())


if __name__ == "__main__":
	server.run(transport="stdio", show_banner=False, log_level="WARNING")
