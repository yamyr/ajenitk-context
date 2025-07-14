"""Tool documentation generator."""

import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from .base import Tool, ToolParameter, ToolParameterType
from .registry import tool_registry


class ToolDocumentationGenerator:
    """Generates documentation for tools in various formats."""
    
    def __init__(self, registry: Optional['ToolRegistry'] = None):
        self.registry = registry or tool_registry
    
    def generate_markdown(self, 
                         tools: Optional[List[Tool]] = None,
                         include_toc: bool = True,
                         include_examples: bool = True) -> str:
        """Generate Markdown documentation for tools.
        
        Args:
            tools: List of tools to document (None for all)
            include_toc: Whether to include table of contents
            include_examples: Whether to include usage examples
        
        Returns:
            Markdown formatted documentation
        """
        if tools is None:
            tools = self.registry.list_tools()
        
        # Sort tools by category and name
        tools_by_category = {}
        for tool in tools:
            category = tool.category
            if category not in tools_by_category:
                tools_by_category[category] = []
            tools_by_category[category].append(tool)
        
        # Sort within categories
        for category in tools_by_category:
            tools_by_category[category].sort(key=lambda t: t.name)
        
        # Build documentation
        lines = []
        lines.append("# Ajentik Tools Documentation")
        lines.append("")
        lines.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append(f"Total tools: {len(tools)}")
        lines.append("")
        
        # Table of contents
        if include_toc:
            lines.append("## Table of Contents")
            lines.append("")
            for category in sorted(tools_by_category.keys()):
                lines.append(f"- [{category.title()}](#{category.replace(' ', '-').lower()})")
                for tool in tools_by_category[category]:
                    lines.append(f"  - [{tool.name}](#{tool.name.replace('_', '-')})")
            lines.append("")
        
        # Document each category
        for category in sorted(tools_by_category.keys()):
            lines.append(f"## {category.title()}")
            lines.append("")
            
            for tool in tools_by_category[category]:
                lines.extend(self._document_tool_markdown(tool, include_examples))
                lines.append("")
        
        return "\n".join(lines)
    
    def _document_tool_markdown(self, tool: Tool, include_examples: bool = True) -> List[str]:
        """Document a single tool in Markdown format."""
        lines = []
        
        # Tool header
        lines.append(f"### {tool.name}")
        lines.append("")
        
        # Metadata
        lines.append(f"**Version:** {tool.version}")
        lines.append(f"**Author:** {tool.author}")
        lines.append(f"**Category:** {tool.category}")
        
        # Safety indicators
        badges = []
        if tool.is_safe:
            badges.append("![Safe](https://img.shields.io/badge/Safe-green)")
        else:
            badges.append("![Unsafe](https://img.shields.io/badge/Unsafe-red)")
        
        if tool.requires_confirmation:
            badges.append("![Requires Confirmation](https://img.shields.io/badge/Requires%20Confirmation-orange)")
        
        if badges:
            lines.append(f"**Safety:** {' '.join(badges)}")
        
        lines.append("")
        
        # Description
        lines.append(f"**Description:** {tool.description}")
        lines.append("")
        
        # Parameters
        if tool.parameters():
            lines.append("#### Parameters")
            lines.append("")
            lines.append("| Name | Type | Required | Description | Default |")
            lines.append("|------|------|----------|-------------|---------|")
            
            for param in tool.parameters():
                required = "✓" if param.required else "✗"
                default = param.default if param.default is not None else "-"
                lines.append(f"| {param.name} | {param.type.value} | {required} | {param.description} | {default} |")
            
            lines.append("")
            
            # Parameter details
            for param in tool.parameters():
                if param.constraints:
                    lines.append(f"- **{param.name} constraints:** {param.constraints}")
        else:
            lines.append("*This tool takes no parameters.*")
            lines.append("")
        
        # Usage example
        if include_examples:
            lines.append("#### Example Usage")
            lines.append("")
            lines.append("```python")
            lines.append(f"from ajentik.tools import tool_registry")
            lines.append("")
            lines.append(f"# Get the tool")
            lines.append(f"tool = tool_registry.get('{tool.name}')")
            lines.append("")
            lines.append(f"# Execute the tool")
            
            # Build example parameters
            example_params = []
            for param in tool.parameters():
                if param.required or param.default is None:
                    # Use example values based on type
                    if param.type == ToolParameterType.STRING:
                        value = f'"example_{param.name}"'
                    elif param.type == ToolParameterType.INTEGER:
                        value = "42"
                    elif param.type == ToolParameterType.FLOAT:
                        value = "3.14"
                    elif param.type == ToolParameterType.BOOLEAN:
                        value = "True"
                    elif param.type == ToolParameterType.FILE_PATH:
                        value = '"/path/to/file"'
                    elif param.type == ToolParameterType.URL:
                        value = '"https://example.com"'
                    elif param.type == ToolParameterType.ARRAY:
                        value = '["item1", "item2"]'
                    elif param.type == ToolParameterType.OBJECT:
                        value = '{"key": "value"}'
                    else:
                        value = "None"
                    
                    example_params.append(f"    {param.name}={value}")
            
            if example_params:
                lines.append("result = tool(")
                lines.append(",\n".join(example_params))
                lines.append(")")
            else:
                lines.append("result = tool()")
            
            lines.append("")
            lines.append("# Check result")
            lines.append("if result.success:")
            lines.append("    print(f'Success: {result.data}')")
            lines.append("else:")
            lines.append("    print(f'Error: {result.error}')")
            lines.append("```")
        
        return lines
    
    def generate_json_schema(self, tools: Optional[List[Tool]] = None) -> Dict[str, Any]:
        """Generate JSON schema for tools.
        
        Args:
            tools: List of tools to document (None for all)
        
        Returns:
            JSON schema dictionary
        """
        if tools is None:
            tools = self.registry.list_tools()
        
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Ajentik Tools Schema",
            "description": "Schema for Ajentik tool definitions",
            "type": "object",
            "properties": {
                "tools": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "category": {"type": "string"},
                            "version": {"type": "string"},
                            "author": {"type": "string"},
                            "is_safe": {"type": "boolean"},
                            "requires_confirmation": {"type": "boolean"},
                            "parameters": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "type": {"type": "string", "enum": [t.value for t in ToolParameterType]},
                                        "description": {"type": "string"},
                                        "required": {"type": "boolean"},
                                        "default": {},
                                        "constraints": {"type": "object"}
                                    },
                                    "required": ["name", "type", "description", "required"]
                                }
                            }
                        },
                        "required": ["name", "description", "category"]
                    }
                }
            }
        }
        
        # Add tool definitions
        tool_definitions = []
        for tool in tools:
            tool_definitions.append(tool.get_schema())
        
        return {
            "schema": schema,
            "tools": tool_definitions
        }
    
    def generate_html(self, 
                      tools: Optional[List[Tool]] = None,
                      template: Optional[str] = None,
                      output_file: Optional[Path] = None) -> str:
        """Generate HTML documentation for tools.
        
        Args:
            tools: List of tools to document (None for all)
            template: Custom HTML template (uses default if None)
            output_file: File to write HTML to (returns string if None)
        
        Returns:
            HTML formatted documentation
        """
        if tools is None:
            tools = self.registry.list_tools()
        
        if template is None:
            template = self._get_default_html_template()
        
        # Prepare data for template
        tools_data = []
        categories = set()
        
        for tool in tools:
            categories.add(tool.category)
            tool_data = {
                "name": tool.name,
                "description": tool.description,
                "category": tool.category,
                "version": tool.version,
                "author": tool.author,
                "is_safe": tool.is_safe,
                "requires_confirmation": tool.requires_confirmation,
                "parameters": []
            }
            
            for param in tool.parameters():
                param_data = {
                    "name": param.name,
                    "type": param.type.value,
                    "description": param.description,
                    "required": param.required,
                    "default": str(param.default) if param.default is not None else None,
                    "constraints": param.constraints
                }
                tool_data["parameters"].append(param_data)
            
            tools_data.append(tool_data)
        
        # Replace template variables
        html = template
        html = html.replace("{{title}}", "Ajentik Tools Documentation")
        html = html.replace("{{generated_date}}", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        html = html.replace("{{tool_count}}", str(len(tools)))
        html = html.replace("{{category_count}}", str(len(categories)))
        html = html.replace("{{tools_json}}", json.dumps(tools_data, indent=2))
        
        if output_file:
            output_file = Path(output_file)
            output_file.write_text(html)
            return f"Documentation written to {output_file}"
        
        return html
    
    def _get_default_html_template(self) -> str:
        """Get default HTML template."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{title}}</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        h1, h2, h3 {
            color: #2c3e50;
        }
        .tool-card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .tool-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .tool-name {
            font-size: 1.5em;
            font-weight: bold;
            color: #3498db;
        }
        .tool-badges {
            display: flex;
            gap: 10px;
        }
        .badge {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
        }
        .badge.safe {
            background-color: #27ae60;
            color: white;
        }
        .badge.unsafe {
            background-color: #e74c3c;
            color: white;
        }
        .badge.confirmation {
            background-color: #f39c12;
            color: white;
        }
        .category-tag {
            display: inline-block;
            padding: 4px 12px;
            background-color: #ecf0f1;
            border-radius: 20px;
            font-size: 0.9em;
            margin-right: 10px;
        }
        .parameters-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        .parameters-table th {
            background-color: #34495e;
            color: white;
            padding: 10px;
            text-align: left;
        }
        .parameters-table td {
            padding: 10px;
            border-bottom: 1px solid #ecf0f1;
        }
        .required {
            color: #e74c3c;
            font-weight: bold;
        }
        .optional {
            color: #95a5a6;
        }
        .metadata {
            color: #7f8c8d;
            font-size: 0.9em;
            margin-top: 10px;
        }
        .filter-controls {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .search-box {
            width: 100%;
            padding: 10px;
            font-size: 16px;
            border: 2px solid #3498db;
            border-radius: 4px;
            margin-bottom: 15px;
        }
        .filter-buttons {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .filter-button {
            padding: 8px 16px;
            border: 2px solid #3498db;
            background: white;
            color: #3498db;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .filter-button:hover {
            background: #3498db;
            color: white;
        }
        .filter-button.active {
            background: #3498db;
            color: white;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #3498db;
        }
        .stat-label {
            color: #7f8c8d;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <h1>{{title}}</h1>
    <p class="metadata">Generated on: {{generated_date}}</p>
    
    <div class="stats">
        <div class="stat-card">
            <div class="stat-number">{{tool_count}}</div>
            <div class="stat-label">Total Tools</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{{category_count}}</div>
            <div class="stat-label">Categories</div>
        </div>
    </div>
    
    <div class="filter-controls">
        <input type="text" class="search-box" id="searchBox" placeholder="Search tools...">
        <div class="filter-buttons" id="categoryFilters">
            <button class="filter-button active" data-category="all">All Categories</button>
        </div>
    </div>
    
    <div id="toolsContainer"></div>
    
    <script>
        const tools = {{tools_json}};
        let currentFilter = 'all';
        let searchQuery = '';
        
        // Build category filters
        const categories = [...new Set(tools.map(t => t.category))];
        const filterContainer = document.getElementById('categoryFilters');
        categories.forEach(category => {
            const button = document.createElement('button');
            button.className = 'filter-button';
            button.textContent = category;
            button.dataset.category = category;
            button.onclick = () => filterByCategory(category);
            filterContainer.appendChild(button);
        });
        
        // Search functionality
        document.getElementById('searchBox').addEventListener('input', (e) => {
            searchQuery = e.target.value.toLowerCase();
            renderTools();
        });
        
        function filterByCategory(category) {
            currentFilter = category;
            document.querySelectorAll('.filter-button').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.category === category);
            });
            renderTools();
        }
        
        function renderTools() {
            const container = document.getElementById('toolsContainer');
            container.innerHTML = '';
            
            const filteredTools = tools.filter(tool => {
                const matchesCategory = currentFilter === 'all' || tool.category === currentFilter;
                const matchesSearch = searchQuery === '' || 
                    tool.name.toLowerCase().includes(searchQuery) ||
                    tool.description.toLowerCase().includes(searchQuery);
                return matchesCategory && matchesSearch;
            });
            
            filteredTools.forEach(tool => {
                const toolCard = createToolCard(tool);
                container.appendChild(toolCard);
            });
        }
        
        function createToolCard(tool) {
            const card = document.createElement('div');
            card.className = 'tool-card';
            
            const badges = [];
            if (tool.is_safe) {
                badges.push('<span class="badge safe">Safe</span>');
            } else {
                badges.push('<span class="badge unsafe">Unsafe</span>');
            }
            if (tool.requires_confirmation) {
                badges.push('<span class="badge confirmation">Requires Confirmation</span>');
            }
            
            const parametersHtml = tool.parameters.length > 0 ? `
                <h3>Parameters</h3>
                <table class="parameters-table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Type</th>
                            <th>Required</th>
                            <th>Description</th>
                            <th>Default</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${tool.parameters.map(param => `
                            <tr>
                                <td><strong>${param.name}</strong></td>
                                <td>${param.type}</td>
                                <td class="${param.required ? 'required' : 'optional'}">${param.required ? '✓' : '✗'}</td>
                                <td>${param.description}</td>
                                <td>${param.default || '-'}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            ` : '<p><em>This tool takes no parameters.</em></p>';
            
            card.innerHTML = `
                <div class="tool-header">
                    <div>
                        <span class="tool-name">${tool.name}</span>
                        <span class="category-tag">${tool.category}</span>
                    </div>
                    <div class="tool-badges">${badges.join('')}</div>
                </div>
                <p>${tool.description}</p>
                ${parametersHtml}
                <div class="metadata">
                    Version: ${tool.version} | Author: ${tool.author}
                </div>
            `;
            
            return card;
        }
        
        // Initial render
        renderTools();
    </script>
</body>
</html>'''
    
    def generate_openapi_spec(self, tools: Optional[List[Tool]] = None) -> Dict[str, Any]:
        """Generate OpenAPI specification for tools as REST endpoints.
        
        Args:
            tools: List of tools to document (None for all)
        
        Returns:
            OpenAPI specification dictionary
        """
        if tools is None:
            tools = self.registry.list_tools()
        
        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "Ajentik Tools API",
                "description": "REST API for Ajentik tools",
                "version": "1.0.0"
            },
            "servers": [
                {
                    "url": "http://localhost:8000",
                    "description": "Development server"
                }
            ],
            "paths": {},
            "components": {
                "schemas": {
                    "ToolResult": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean"},
                            "data": {},
                            "error": {"type": "string"},
                            "metadata": {"type": "object"},
                            "execution_time": {"type": "number"},
                            "timestamp": {"type": "string", "format": "date-time"}
                        },
                        "required": ["success"]
                    }
                }
            }
        }
        
        # Add each tool as an endpoint
        for tool in tools:
            path = f"/tools/{tool.category}/{tool.name}"
            
            # Build request body schema
            properties = {}
            required = []
            
            for param in tool.parameters():
                prop_schema = {"description": param.description}
                
                # Map parameter types to OpenAPI types
                if param.type == ToolParameterType.STRING:
                    prop_schema["type"] = "string"
                elif param.type == ToolParameterType.INTEGER:
                    prop_schema["type"] = "integer"
                elif param.type == ToolParameterType.FLOAT:
                    prop_schema["type"] = "number"
                elif param.type == ToolParameterType.BOOLEAN:
                    prop_schema["type"] = "boolean"
                elif param.type == ToolParameterType.ARRAY:
                    prop_schema["type"] = "array"
                    prop_schema["items"] = {}
                elif param.type == ToolParameterType.OBJECT:
                    prop_schema["type"] = "object"
                elif param.type == ToolParameterType.FILE_PATH:
                    prop_schema["type"] = "string"
                    prop_schema["format"] = "path"
                elif param.type == ToolParameterType.URL:
                    prop_schema["type"] = "string"
                    prop_schema["format"] = "uri"
                
                if param.default is not None:
                    prop_schema["default"] = param.default
                
                properties[param.name] = prop_schema
                
                if param.required:
                    required.append(param.name)
            
            spec["paths"][path] = {
                "post": {
                    "summary": tool.name,
                    "description": tool.description,
                    "tags": [tool.category],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": properties,
                                    "required": required
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Tool executed successfully",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ToolResult"}
                                }
                            }
                        },
                        "400": {
                            "description": "Invalid parameters"
                        },
                        "500": {
                            "description": "Tool execution error"
                        }
                    }
                }
            }
        
        return spec
    
    def write_documentation(self,
                          output_dir: Path,
                          formats: List[str] = None,
                          tools: Optional[List[Tool]] = None):
        """Write documentation in multiple formats to a directory.
        
        Args:
            output_dir: Directory to write documentation to
            formats: List of formats to generate (default: all)
            tools: List of tools to document (None for all)
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if formats is None:
            formats = ["markdown", "json", "html", "openapi"]
        
        if tools is None:
            tools = self.registry.list_tools()
        
        results = {}
        
        if "markdown" in formats:
            md_content = self.generate_markdown(tools)
            md_file = output_dir / "tools.md"
            md_file.write_text(md_content)
            results["markdown"] = str(md_file)
        
        if "json" in formats:
            json_schema = self.generate_json_schema(tools)
            json_file = output_dir / "tools-schema.json"
            json_file.write_text(json.dumps(json_schema, indent=2))
            results["json"] = str(json_file)
        
        if "html" in formats:
            html_file = output_dir / "tools.html"
            self.generate_html(tools, output_file=html_file)
            results["html"] = str(html_file)
        
        if "openapi" in formats:
            openapi_spec = self.generate_openapi_spec(tools)
            openapi_file = output_dir / "tools-openapi.json"
            openapi_file.write_text(json.dumps(openapi_spec, indent=2))
            results["openapi"] = str(openapi_file)
        
        return results