"""Code analysis agent implementation."""

import ast
import re
from typing import Any, Dict, List, Optional

from pydantic_ai import RunContext

from ..models.schemas import (
    AgentConfig,
    AgentRole,
    CodeAnalysisRequest,
    CodeAnalysisResponse,
    CodeIssue,
)
from ..utils.dependencies import AnalysisAgentDependencies
from .base_agent import BaseAgent


class AnalysisAgent(BaseAgent[CodeAnalysisResponse, AnalysisAgentDependencies]):
    """Agent specialized in code analysis tasks."""
    
    def __init__(self, config: Optional[AgentConfig] = None):
        """Initialize the analysis agent."""
        if config is None:
            config = AgentConfig(
                name="code_analyzer",
                role=AgentRole.CODE_ANALYZER,
                model="openai:gpt-4o",
                temperature=0.2,  # Lower temperature for consistent analysis
                tools=["analyze_structure", "detect_issues", "calculate_metrics", "suggest_fixes"]
            )
        
        super().__init__(
            config=config,
            output_type=CodeAnalysisResponse,
            dependencies_type=AnalysisAgentDependencies
        )
    
    def get_default_prompt(self) -> str:
        """Get the default system prompt for code analysis."""
        return """You are an expert code analysis agent. Your role is to:

1. Analyze code for quality, security, and performance issues
2. Identify bugs, vulnerabilities, and anti-patterns
3. Calculate code metrics and complexity
4. Provide actionable suggestions for improvement
5. Follow industry best practices and standards
6. Consider maintainability and scalability

Always structure your response as a CodeAnalysisResponse with:
- summary: A concise summary of the analysis
- issues: List of identified issues with severity and suggestions
- metrics: Dictionary of calculated metrics
- suggestions: List of general improvement suggestions
- overall_score: Overall code quality score (0.0-10.0)

Focus on providing:
- Accurate and relevant issue detection
- Clear and actionable suggestions
- Balanced assessment considering context
- Prioritized issues by severity"""
    
    def _register_tools(self) -> None:
        """Register code analysis specific tools."""
        
        @self.agent.tool
        async def analyze_structure(
            ctx: RunContext[AnalysisAgentDependencies],
            code: str,
            language: str
        ) -> Dict[str, Any]:
            """Analyze code structure and complexity."""
            structure = {
                "lines_of_code": len(code.splitlines()),
                "functions": 0,
                "classes": 0,
                "imports": 0,
                "complexity": 0
            }
            
            if language == "python":
                try:
                    tree = ast.parse(code)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            structure["functions"] += 1
                        elif isinstance(node, ast.ClassDef):
                            structure["classes"] += 1
                        elif isinstance(node, (ast.Import, ast.ImportFrom)):
                            structure["imports"] += 1
                        elif isinstance(node, (ast.If, ast.For, ast.While)):
                            structure["complexity"] += 1
                except:
                    pass
            
            return structure
        
        @self.agent.tool
        async def detect_security_issues(
            ctx: RunContext[AnalysisAgentDependencies],
            code: str,
            language: str
        ) -> List[Dict[str, Any]]:
            """Detect potential security issues."""
            issues = []
            
            # Common security patterns to check
            security_patterns = {
                "sql_injection": r"(query|execute)\s*\(\s*[\"'].*%[s|d].*[\"']\s*%",
                "hardcoded_secret": r"(password|secret|key|token)\s*=\s*[\"'][^\"']+[\"']",
                "eval_usage": r"\beval\s*\(",
                "exec_usage": r"\bexec\s*\(",
                "pickle_usage": r"pickle\.(load|loads)\s*\(",
                "shell_injection": r"os\.(system|popen)\s*\(",
            }
            
            for issue_type, pattern in security_patterns.items():
                matches = re.finditer(pattern, code, re.IGNORECASE)
                for match in matches:
                    line_no = code[:match.start()].count('\n') + 1
                    issues.append({
                        "type": "security",
                        "subtype": issue_type,
                        "line": line_no,
                        "severity": "high" if issue_type in ["sql_injection", "shell_injection"] else "medium",
                        "message": f"Potential {issue_type.replace('_', ' ')} vulnerability detected"
                    })
            
            return issues
        
        @self.agent.tool
        async def detect_code_smells(
            ctx: RunContext[AnalysisAgentDependencies],
            code: str,
            language: str
        ) -> List[Dict[str, Any]]:
            """Detect code smells and anti-patterns."""
            smells = []
            
            lines = code.splitlines()
            
            # Check for various code smells
            for i, line in enumerate(lines, 1):
                # Long lines
                if len(line) > 120:
                    smells.append({
                        "type": "style",
                        "line": i,
                        "severity": "low",
                        "message": f"Line too long ({len(line)} characters)"
                    })
                
                # Deep nesting (simple check based on indentation)
                indent_level = len(line) - len(line.lstrip())
                if indent_level > 20:  # 5 levels of 4-space indentation
                    smells.append({
                        "type": "complexity",
                        "line": i,
                        "severity": "medium",
                        "message": "Deep nesting detected - consider refactoring"
                    })
                
                # TODO/FIXME comments
                if "TODO" in line or "FIXME" in line:
                    smells.append({
                        "type": "maintenance",
                        "line": i,
                        "severity": "low",
                        "message": "Unresolved TODO/FIXME comment"
                    })
            
            return smells
        
        @self.agent.tool
        async def calculate_metrics(
            ctx: RunContext[AnalysisAgentDependencies],
            code: str,
            structure: Dict[str, Any]
        ) -> Dict[str, float]:
            """Calculate code quality metrics."""
            lines = code.splitlines()
            
            # Basic metrics
            total_lines = len(lines)
            code_lines = len([l for l in lines if l.strip() and not l.strip().startswith('#')])
            comment_lines = len([l for l in lines if l.strip().startswith('#')])
            blank_lines = len([l for l in lines if not l.strip()])
            
            metrics = {
                "total_lines": total_lines,
                "code_lines": code_lines,
                "comment_lines": comment_lines,
                "blank_lines": blank_lines,
                "comment_ratio": comment_lines / max(code_lines, 1),
                "complexity_per_function": structure.get("complexity", 0) / max(structure.get("functions", 1), 1)
            }
            
            return metrics
        
        @self.agent.tool
        async def suggest_refactoring(
            ctx: RunContext[AnalysisAgentDependencies],
            issues: List[Dict[str, Any]],
            metrics: Dict[str, float]
        ) -> List[str]:
            """Suggest refactoring based on issues and metrics."""
            suggestions = []
            
            # Based on metrics
            if metrics.get("comment_ratio", 0) < 0.1:
                suggestions.append("Add more comments to improve code documentation")
            
            if metrics.get("complexity_per_function", 0) > 5:
                suggestions.append("Consider breaking down complex functions into smaller ones")
            
            # Based on issues
            security_issues = [i for i in issues if i.get("type") == "security"]
            if security_issues:
                suggestions.append("Address security vulnerabilities as top priority")
            
            high_severity = [i for i in issues if i.get("severity") == "high"]
            if len(high_severity) > 3:
                suggestions.append("Focus on resolving high-severity issues first")
            
            return suggestions
    
    async def analyze_code(
        self,
        request: CodeAnalysisRequest,
        deps: Optional[AnalysisAgentDependencies] = None
    ) -> CodeAnalysisResponse:
        """
        Analyze code based on the request.
        
        Args:
            request: Code analysis request
            deps: Optional dependencies override
        
        Returns:
            Code analysis response
        """
        if deps is None:
            deps = AnalysisAgentDependencies(
                settings=self.config.settings,
                config=self.config,
                analysis_types=request.analysis_types,
                include_suggestions=request.include_suggestions
            )
        
        # Build prompt from request
        prompt = f"""Analyze the following {request.language} code:

```{request.language}
{request.code}
```

Focus on: {', '.join(request.analysis_types)}
Include suggestions: {request.include_suggestions}"""
        
        # Run the agent
        response = await self.run(prompt, deps)
        
        return response
    
    def analyze_code_sync(
        self,
        request: CodeAnalysisRequest,
        deps: Optional[AnalysisAgentDependencies] = None
    ) -> CodeAnalysisResponse:
        """Synchronous version of analyze_code."""
        import asyncio
        return asyncio.run(self.analyze_code(request, deps))