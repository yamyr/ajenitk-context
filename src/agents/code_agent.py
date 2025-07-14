"""Code generation agent implementation."""

import re
from typing import Dict, List, Optional

from pydantic_ai import RunContext

from ..models.schemas import (
    AgentConfig,
    AgentRole,
    CodeGenerationRequest,
    CodeGenerationResponse,
)
from ..utils.dependencies import CodeAgentDependencies
from .base_agent import BaseAgent


class CodeAgent(BaseAgent[CodeGenerationResponse, CodeAgentDependencies]):
    """Agent specialized in code generation tasks."""
    
    def __init__(self, config: Optional[AgentConfig] = None):
        """Initialize the code agent."""
        if config is None:
            config = AgentConfig(
                name="code_generator",
                role=AgentRole.CODE_GENERATOR,
                model="openai:gpt-4o",
                temperature=0.3,  # Lower temperature for code generation
                tools=["analyze_requirements", "generate_code", "validate_syntax"]
            )
        
        super().__init__(
            config=config,
            output_type=CodeGenerationResponse,
            dependencies_type=CodeAgentDependencies
        )
    
    def get_default_prompt(self) -> str:
        """Get the default system prompt for code generation."""
        return """You are an expert code generation agent. Your role is to:

1. Analyze requirements and generate high-quality, production-ready code
2. Follow best practices and design patterns for the specified language
3. Include proper error handling and validation
4. Write clean, maintainable, and well-documented code
5. Consider performance and security implications
6. Provide clear explanations of the generated code

Always structure your response as a CodeGenerationResponse with:
- code: The generated code
- language: The programming language used
- explanation: Brief explanation of the code
- dependencies: List of required dependencies/imports
- warnings: Any potential issues or considerations
- confidence_score: Your confidence in the solution (0.0-1.0)

Focus on creating code that is:
- Correct and functional
- Efficient and optimized
- Secure and robust
- Easy to understand and maintain"""
    
    def _register_tools(self) -> None:
        """Register code generation specific tools."""
        
        @self.agent.tool
        async def analyze_requirements(
            ctx: RunContext[CodeAgentDependencies],
            requirements: str
        ) -> Dict[str, Any]:
            """Analyze code requirements and extract key information."""
            # This would typically call an external service or use more sophisticated analysis
            language = ctx.deps.language
            framework = ctx.deps.framework
            
            # Simple pattern matching for requirements
            patterns = {
                "api": r"\b(api|endpoint|rest|graphql)\b",
                "database": r"\b(database|db|sql|orm|query)\b",
                "auth": r"\b(auth|authentication|login|security)\b",
                "ui": r"\b(ui|frontend|component|react|vue)\b",
                "test": r"\b(test|testing|unit|integration)\b",
            }
            
            detected_features = []
            for feature, pattern in patterns.items():
                if re.search(pattern, requirements.lower()):
                    detected_features.append(feature)
            
            return {
                "language": language,
                "framework": framework,
                "detected_features": detected_features,
                "complexity": "high" if len(detected_features) > 3 else "medium"
            }
        
        @self.agent.tool
        async def generate_code_snippet(
            ctx: RunContext[CodeAgentDependencies],
            purpose: str,
            context: Optional[str] = None
        ) -> str:
            """Generate a specific code snippet."""
            language = ctx.deps.language
            
            # This is a simplified example - in reality, this might use
            # templates, AST manipulation, or other code generation techniques
            if language == "python":
                if "function" in purpose.lower():
                    return f"""def generated_function():
    \"\"\"Generated function for: {purpose}\"\"\"
    # TODO: Implement {purpose}
    pass"""
                elif "class" in purpose.lower():
                    return f"""class GeneratedClass:
    \"\"\"Generated class for: {purpose}\"\"\"
    
    def __init__(self):
        # TODO: Initialize for {purpose}
        pass"""
            
            return f"// Generated code for: {purpose}"
        
        @self.agent.tool
        async def validate_syntax(
            ctx: RunContext[CodeAgentDependencies],
            code: str
        ) -> Dict[str, Any]:
            """Validate code syntax (simplified)."""
            language = ctx.deps.language
            
            # In a real implementation, this would use language-specific
            # parsers or linters
            is_valid = True
            errors = []
            
            if language == "python":
                try:
                    compile(code, "<string>", "exec")
                except SyntaxError as e:
                    is_valid = False
                    errors.append(f"Syntax error at line {e.lineno}: {e.msg}")
            
            return {
                "is_valid": is_valid,
                "errors": errors,
                "language": language
            }
        
        @self.agent.tool
        async def suggest_improvements(
            ctx: RunContext[CodeAgentDependencies],
            code: str
        ) -> List[str]:
            """Suggest code improvements."""
            suggestions = []
            
            # Simple pattern-based suggestions
            if ctx.deps.language == "python":
                if "except:" in code:
                    suggestions.append("Avoid bare except clauses - specify exception types")
                if "import *" in code:
                    suggestions.append("Avoid wildcard imports - import specific names")
                if not re.search(r'""".*?"""', code, re.DOTALL):
                    suggestions.append("Add docstrings to functions and classes")
                if "TODO" in code or "FIXME" in code:
                    suggestions.append("Complete TODO/FIXME items before production")
            
            return suggestions
    
    async def generate_code(
        self,
        request: CodeGenerationRequest,
        deps: Optional[CodeAgentDependencies] = None
    ) -> CodeGenerationResponse:
        """
        Generate code based on the request.
        
        Args:
            request: Code generation request
            deps: Optional dependencies override
        
        Returns:
            Generated code response
        """
        if deps is None:
            deps = CodeAgentDependencies(
                settings=self.config.settings,
                config=self.config,
                language=request.language,
                framework=request.framework
            )
        else:
            deps.language = request.language
            deps.framework = request.framework
        
        # Build prompt from request
        prompt = f"""Generate {request.language} code for: {request.description}"""
        
        if request.requirements:
            prompt += f"\n\nRequirements:\n" + "\n".join(f"- {req}" for req in request.requirements)
        
        if request.constraints:
            prompt += f"\n\nConstraints:\n" + "\n".join(f"- {constraint}" for constraint in request.constraints)
        
        if request.examples:
            prompt += f"\n\nExamples for reference:\n" + "\n".join(request.examples)
        
        # Run the agent
        response = await self.run(prompt, deps)
        
        return response
    
    def generate_code_sync(
        self,
        request: CodeGenerationRequest,
        deps: Optional[CodeAgentDependencies] = None
    ) -> CodeGenerationResponse:
        """Synchronous version of generate_code."""
        import asyncio
        return asyncio.run(self.generate_code(request, deps))