#!/usr/bin/env python3
"""
Code Generation Example

This example demonstrates how to use the CodeAgent to generate code.
It shows:
- Creating code generation requests
- Specifying languages and frameworks
- Handling generated code
- Working with dependencies and warnings
"""

import asyncio
from pathlib import Path
from src.agents import CodeAgent
from src.models import CodeGenerationRequest


async def main():
    # Create a code agent
    print("Creating Code Agent...")
    agent = CodeAgent()
    
    # Example 1: Generate a simple Python function
    print("\n" + "="*50)
    print("Example 1: Python Function")
    print("="*50 + "\n")
    
    request1 = CodeGenerationRequest(
        description="Create a function that calculates the Fibonacci sequence up to n terms",
        language="python",
        requirements=[
            "Use memoization for optimization",
            "Include type hints",
            "Add comprehensive docstring",
            "Handle edge cases (n < 0, n = 0, n = 1)"
        ]
    )
    
    response1 = await agent.generate_code(request1)
    
    print(f"Language: {response1.language}")
    print(f"\nGenerated Code:\n{'-'*40}")
    print(response1.code)
    print('-'*40)
    
    if response1.explanation:
        print(f"\nExplanation: {response1.explanation}")
    
    if response1.dependencies:
        print("\nDependencies:")
        for dep in response1.dependencies:
            print(f"  - {dep}")
    
    # Example 2: Generate a React component
    print("\n" + "="*50)
    print("Example 2: React Component")
    print("="*50 + "\n")
    
    request2 = CodeGenerationRequest(
        description="Create a React component for a todo list with add, delete, and toggle complete functionality",
        language="typescript",
        framework="react",
        requirements=[
            "Use functional component with hooks",
            "Include TypeScript interfaces",
            "Style with CSS modules",
            "Make it accessible (ARIA attributes)",
            "Include local storage persistence"
        ]
    )
    
    response2 = await agent.generate_code(request2)
    
    print(f"Language: {response2.language}")
    print(f"Framework: {response2.framework}")
    print(f"\nGenerated Code:\n{'-'*40}")
    print(response2.code)
    print('-'*40)
    
    if response2.warnings:
        print("\n⚠️  Warnings:")
        for warning in response2.warnings:
            print(f"  - {warning}")
    
    # Example 3: Generate SQL schema
    print("\n" + "="*50)
    print("Example 3: SQL Database Schema")
    print("="*50 + "\n")
    
    request3 = CodeGenerationRequest(
        description="Create a SQL schema for an e-commerce platform",
        language="sql",
        requirements=[
            "Include tables for users, products, orders, and order items",
            "Add appropriate indexes",
            "Include foreign key constraints",
            "Add created_at and updated_at timestamps",
            "Support product categories and tags"
        ],
        constraints=[
            "Use PostgreSQL syntax",
            "Follow naming conventions (snake_case)",
            "Include comments for complex fields"
        ]
    )
    
    response3 = await agent.generate_code(request3)
    
    print(f"Generated SQL Schema:\n{'-'*40}")
    print(response3.code)
    print('-'*40)
    
    # Save generated code to files
    print("\n" + "="*50)
    print("Saving Generated Code")
    print("="*50 + "\n")
    
    # Create output directory
    output_dir = Path("generated_code")
    output_dir.mkdir(exist_ok=True)
    
    # Save Python function
    python_file = output_dir / "fibonacci.py"
    python_file.write_text(response1.code)
    print(f"✅ Saved Python code to: {python_file}")
    
    # Save React component
    react_file = output_dir / "TodoList.tsx"
    react_file.write_text(response2.code)
    print(f"✅ Saved React component to: {react_file}")
    
    # Save SQL schema
    sql_file = output_dir / "ecommerce_schema.sql"
    sql_file.write_text(response3.code)
    print(f"✅ Saved SQL schema to: {sql_file}")
    
    print("\nCode generation examples completed!")


if __name__ == "__main__":
    asyncio.run(main())