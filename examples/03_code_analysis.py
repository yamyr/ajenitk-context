#!/usr/bin/env python3
"""
Code Analysis Example

This example demonstrates how to use the AnalysisAgent to analyze code.
It shows:
- Analyzing code for quality issues
- Security vulnerability detection
- Performance analysis
- Getting improvement suggestions
"""

import asyncio
from pathlib import Path
from src.agents import AnalysisAgent
from src.models import CodeAnalysisRequest


# Sample code to analyze
SAMPLE_PYTHON_CODE = """
import mysql.connector
import hashlib

class UserManager:
    def __init__(self):
        self.db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="password123",  # Hardcoded password
            database="users"
        )
    
    def create_user(self, username, password, email):
        cursor = self.db.cursor()
        # SQL injection vulnerability
        query = f"INSERT INTO users (username, password, email) VALUES ('{username}', '{password}', '{email}')"
        cursor.execute(query)
        self.db.commit()
        
    def authenticate(self, username, password):
        cursor = self.db.cursor()
        # Weak password hashing
        hashed = hashlib.md5(password.encode()).hexdigest()
        query = f"SELECT * FROM users WHERE username='{username}' AND password='{hashed}'"
        cursor.execute(query)
        return cursor.fetchone()
    
    def get_all_users(self):
        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM users")
        users = []
        for user in cursor.fetchall():
            users.append(user)  # Inefficient list building
        return users
"""

SAMPLE_JAVASCRIPT_CODE = """
// User authentication service
const bcrypt = require('bcrypt');

class AuthService {
    constructor(database) {
        this.db = database;
        this.secretKey = 'my-secret-key';  // Hardcoded secret
    }
    
    async login(username, password) {
        // No input validation
        const user = await this.db.findOne({ username: username });
        
        if (!user) {
            return null;
        }
        
        // Synchronous bcrypt comparison (blocks event loop)
        const isValid = bcrypt.compareSync(password, user.password);
        
        if (isValid) {
            // Predictable token generation
            const token = Buffer.from(username + ':' + Date.now()).toString('base64');
            return { user, token };
        }
        
        return null;
    }
    
    async register(userData) {
        // No email validation
        // No password strength check
        const hashedPassword = bcrypt.hashSync(userData.password, 10);
        
        const newUser = {
            ...userData,
            password: hashedPassword,
            createdAt: new Date()
        };
        
        // No error handling
        return this.db.insert(newUser);
    }
}

module.exports = AuthService;
"""


async def main():
    # Create an analysis agent
    print("Creating Analysis Agent...")
    agent = AnalysisAgent()
    
    # Example 1: Analyze Python code
    print("\n" + "="*50)
    print("Example 1: Python Code Analysis")
    print("="*50 + "\n")
    
    python_request = CodeAnalysisRequest(
        code=SAMPLE_PYTHON_CODE,
        language="python",
        analysis_types=["security", "quality", "performance"],
        include_suggestions=True
    )
    
    python_analysis = await agent.analyze_code(python_request)
    
    print(f"📊 Analysis Summary:\n{python_analysis.summary}\n")
    
    if python_analysis.issues:
        print("🚨 Issues Found:")
        for issue in python_analysis.issues:
            severity_emoji = {
                "high": "🔴",
                "medium": "🟡", 
                "low": "🟢"
            }.get(issue.severity, "⚪")
            
            print(f"\n{severity_emoji} [{issue.severity.upper()}] {issue.type}")
            print(f"   Description: {issue.description}")
            if issue.line_number:
                print(f"   Line: {issue.line_number}")
            if issue.suggestion:
                print(f"   Suggestion: {issue.suggestion}")
    
    if python_analysis.metrics:
        print("\n📈 Code Metrics:")
        for metric, value in python_analysis.metrics.items():
            print(f"   {metric}: {value}")
    
    if python_analysis.suggestions:
        print("\n💡 Improvement Suggestions:")
        for i, suggestion in enumerate(python_analysis.suggestions, 1):
            print(f"   {i}. {suggestion}")
    
    print(f"\n🎯 Overall Score: {python_analysis.overall_score}/10.0")
    
    # Example 2: Analyze JavaScript code
    print("\n" + "="*50)
    print("Example 2: JavaScript Code Analysis")
    print("="*50 + "\n")
    
    js_request = CodeAnalysisRequest(
        code=SAMPLE_JAVASCRIPT_CODE,
        language="javascript",
        analysis_types=["security", "performance", "best-practices"],
        include_suggestions=True,
        context="Node.js authentication service"
    )
    
    js_analysis = await agent.analyze_code(js_request)
    
    print(f"📊 Analysis Summary:\n{js_analysis.summary}\n")
    
    # Display issues in a table format
    if js_analysis.issues:
        print("🚨 Security & Quality Issues:\n")
        print(f"{'Type':<20} {'Severity':<10} {'Description':<50}")
        print("-" * 80)
        
        for issue in js_analysis.issues:
            desc = issue.description[:47] + "..." if len(issue.description) > 50 else issue.description
            print(f"{issue.type:<20} {issue.severity:<10} {desc:<50}")
    
    # Example 3: Quick security scan
    print("\n" + "="*50)
    print("Example 3: Quick Security Scan")
    print("="*50 + "\n")
    
    security_request = CodeAnalysisRequest(
        code=SAMPLE_PYTHON_CODE,
        language="python",
        analysis_types=["security"],  # Only security analysis
        include_suggestions=True
    )
    
    security_analysis = await agent.analyze_code(security_request)
    
    print("🔒 Security Analysis Results:\n")
    
    security_issues = [issue for issue in security_analysis.issues if issue.type == "security"]
    
    if security_issues:
        print(f"Found {len(security_issues)} security vulnerabilities:\n")
        for issue in security_issues:
            print(f"⚠️  {issue.description}")
            if issue.suggestion:
                print(f"   Fix: {issue.suggestion}")
            print()
    else:
        print("✅ No security vulnerabilities detected!")
    
    # Example 4: Analyze a file
    print("\n" + "="*50)
    print("Example 4: Analyzing a File")
    print("="*50 + "\n")
    
    # Create a sample file to analyze
    sample_file = Path("sample_code.py")
    sample_file.write_text("""
def calculate_discount(price, discount_percent):
    # Missing input validation
    discounted_price = price * (1 - discount_percent / 100)
    return discounted_price

def process_payment(amount, card_number):
    # Logging sensitive data
    print(f"Processing payment of ${amount} with card {card_number}")
    # Simplified payment logic
    return True

# Global variable (code smell)
total_sales = 0

def record_sale(amount):
    global total_sales
    total_sales += amount  # Not thread-safe
""")
    
    file_content = sample_file.read_text()
    
    file_request = CodeAnalysisRequest(
        code=file_content,
        language="python",
        analysis_types=["quality", "security", "maintainability"],
        include_suggestions=True,
        context=f"File: {sample_file.name}"
    )
    
    file_analysis = await agent.analyze_code(file_request)
    
    print(f"📁 Analyzing: {sample_file.name}")
    print(f"\n{file_analysis.summary}")
    
    # Generate a report
    print("\n" + "="*50)
    print("Generating Analysis Report")
    print("="*50 + "\n")
    
    report = f"""
# Code Analysis Report

Generated: {asyncio.get_event_loop().time()}

## File: {sample_file.name}

### Summary
{file_analysis.summary}

### Issues Found
"""
    
    for issue in file_analysis.issues:
        report += f"\n- **{issue.type}** ({issue.severity}): {issue.description}"
        if issue.line_number:
            report += f" (Line {issue.line_number})"
    
    report += f"\n\n### Overall Score: {file_analysis.overall_score}/10.0\n"
    
    # Save report
    report_file = Path("analysis_report.md")
    report_file.write_text(report)
    print(f"✅ Report saved to: {report_file}")
    
    # Cleanup
    sample_file.unlink()
    
    print("\nCode analysis examples completed!")


if __name__ == "__main__":
    asyncio.run(main())