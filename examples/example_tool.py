"""Example custom tool demonstrating the Ajentik tool system."""

import requests
from typing import Dict, Any

from src.tools import tool, async_tool, ToolResult


# Simple synchronous tool using decorator
@tool(
    name="weather_info",
    description="Get current weather information for a city",
    category="weather",
    is_safe=True
)
def get_weather(city: str, units: str = "metric") -> Dict[str, Any]:
    """Get weather information for a city.
    
    Args:
        city: Name of the city
        units: Temperature units (metric/imperial)
    
    Returns:
        Weather data dictionary
    """
    # This is a mock implementation
    # In real use, you would call a weather API
    return {
        "city": city,
        "temperature": 22 if units == "metric" else 72,
        "unit": "°C" if units == "metric" else "°F",
        "conditions": "Partly cloudy",
        "humidity": 65,
        "wind_speed": 15
    }


# Async tool example
@async_tool(
    name="web_scraper",
    description="Scrape content from a webpage",
    category="web",
    requires_confirmation=True,
    is_safe=False
)
async def scrape_webpage(url: str, selector: str = None) -> str:
    """Scrape content from a webpage.
    
    Args:
        url: URL to scrape
        selector: Optional CSS selector
    
    Returns:
        Scraped content
    """
    # Mock implementation
    # Real implementation would use aiohttp and beautifulsoup
    return f"Content from {url}" + (f" matching {selector}" if selector else "")


# Tool that returns ToolResult directly
@tool(
    name="calculator",
    description="Perform basic calculations",
    category="math",
    is_safe=True
)
def calculate(expression: str) -> ToolResult:
    """Evaluate a mathematical expression.
    
    Args:
        expression: Mathematical expression to evaluate
    
    Returns:
        ToolResult with the calculation result
    """
    try:
        # In production, use a safe expression evaluator
        # This is just for demonstration
        allowed_chars = "0123456789+-*/()., "
        if all(c in allowed_chars for c in expression):
            result = eval(expression)
            return ToolResult(
                success=True,
                data={"result": result, "expression": expression},
                metadata={"type": "calculation"}
            )
        else:
            return ToolResult(
                success=False,
                error="Invalid characters in expression"
            )
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Calculation error: {str(e)}"
        )


# Tool with multiple parameter types
@tool(
    name="data_processor",
    description="Process data with various options",
    category="data",
    is_safe=True
)
def process_data(
    data: list,
    operation: str,
    threshold: float = 0.5,
    include_stats: bool = True,
    output_format: str = "json"
) -> Dict[str, Any]:
    """Process data with specified operation.
    
    Args:
        data: List of values to process
        operation: Operation to perform (sum/average/filter)
        threshold: Threshold for filtering
        include_stats: Whether to include statistics
        output_format: Output format (json/csv)
    
    Returns:
        Processed data and optional statistics
    """
    result = {"operation": operation, "format": output_format}
    
    if operation == "sum":
        result["result"] = sum(data)
    elif operation == "average":
        result["result"] = sum(data) / len(data) if data else 0
    elif operation == "filter":
        result["result"] = [x for x in data if x > threshold]
    else:
        result["error"] = f"Unknown operation: {operation}"
    
    if include_stats and "error" not in result:
        result["stats"] = {
            "count": len(data),
            "min": min(data) if data else None,
            "max": max(data) if data else None
        }
    
    return result


# Tool that demonstrates parameter validation
@tool(
    name="file_analyzer",
    description="Analyze a file and provide insights",
    category="file_system",
    requires_confirmation=True,
    is_safe=False,
    aliases=["analyze_file", "file_info"]
)
def analyze_file(
    path: str,
    analysis_type: str = "basic",
    max_size_mb: int = 10
) -> Dict[str, Any]:
    """Analyze a file and return insights.
    
    Args:
        path: Path to the file
        analysis_type: Type of analysis (basic/detailed/security)
        max_size_mb: Maximum file size to analyze in MB
    
    Returns:
        File analysis results
    """
    # Mock implementation
    import os
    from pathlib import Path
    
    file_path = Path(path)
    
    if not file_path.exists():
        return {"error": f"File not found: {path}"}
    
    stat = file_path.stat()
    size_mb = stat.st_size / (1024 * 1024)
    
    if size_mb > max_size_mb:
        return {"error": f"File too large: {size_mb:.1f}MB (max: {max_size_mb}MB)"}
    
    analysis = {
        "path": str(file_path.absolute()),
        "size": stat.st_size,
        "size_human": f"{size_mb:.2f}MB",
        "type": file_path.suffix,
        "modified": stat.st_mtime
    }
    
    if analysis_type in ["detailed", "security"]:
        analysis["permissions"] = oct(stat.st_mode)[-3:]
        analysis["owner"] = stat.st_uid
    
    if analysis_type == "security":
        # Mock security checks
        analysis["security"] = {
            "executable": os.access(path, os.X_OK),
            "writable": os.access(path, os.W_OK),
            "suspicious_extensions": file_path.suffix in ['.exe', '.bat', '.sh']
        }
    
    return analysis


if __name__ == "__main__":
    # Test the tools
    print("Testing weather tool:")
    result = get_weather("London", "metric")
    print(result)
    
    print("\nTesting calculator tool:")
    calc_result = calculate("2 + 2 * 3")
    print(calc_result)
    
    print("\nTesting data processor:")
    data_result = process_data([1, 2, 3, 4, 5], "average")
    print(data_result)