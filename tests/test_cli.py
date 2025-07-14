"""Tests for CLI commands."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from click.testing import CliRunner

from src.cli.main import cli


class TestCLIBasics:
    """Test basic CLI functionality."""
    
    def test_cli_help(self, cli_runner):
        """Test CLI help command."""
        result = cli_runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert "Ajentik AI CLI" in result.output
        assert "chat" in result.output
        assert "code" in result.output
        assert "monitor" in result.output
    
    def test_cli_version(self, cli_runner):
        """Test version command."""
        result = cli_runner.invoke(cli, ['version'])
        assert result.exit_code == 0
        assert "Ajentik AI System" in result.output
        assert "Version:" in result.output
        assert "Python:" in result.output
    
    def test_cli_debug_flag(self, cli_runner):
        """Test debug flag."""
        with patch('src.utils.setup_logfire') as mock_setup:
            result = cli_runner.invoke(cli, ['--debug', '--no-logfire', 'version'])
            assert result.exit_code == 0
            mock_setup.assert_not_called()
    
    def test_cli_no_logfire_flag(self, cli_runner):
        """Test --no-logfire flag."""
        with patch('src.utils.setup_logfire') as mock_setup:
            result = cli_runner.invoke(cli, ['--no-logfire', 'version'])
            assert result.exit_code == 0
            mock_setup.assert_not_called()


class TestChatCommand:
    """Test chat command functionality."""
    
    @patch('src.agents.ChatAgent')
    def test_chat_basic(self, mock_agent_class, cli_runner):
        """Test basic chat interaction."""
        # Mock agent
        mock_agent = MagicMock()
        mock_response = MagicMock()
        mock_response.message = "Hello! How can I help?"
        mock_response.confidence = 0.95
        mock_response.suggested_actions = []
        mock_agent.chat_sync.return_value = mock_response
        mock_agent_class.return_value = mock_agent
        
        # Simulate chat with immediate exit
        with patch('rich.prompt.Prompt.ask', side_effect=['Hello', 'exit']):
            result = cli_runner.invoke(cli, ['chat'])
            
            assert result.exit_code == 0
            assert "Starting chat session" in result.output
            assert "Goodbye!" in result.output
            mock_agent.chat_sync.assert_called_once()
    
    @patch('src.agents.ChatAgent')
    def test_chat_enhanced_mode(self, mock_agent_class, cli_runner):
        """Test enhanced chat mode."""
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent
        
        with patch('src.cli.chat_interface.InteractiveChatSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session
            
            result = cli_runner.invoke(cli, ['chat', '--enhanced'])
            
            assert result.exit_code == 0
            mock_session.run.assert_called_once()
    
    @patch('src.agents.ChatAgent')
    def test_chat_with_personality(self, mock_agent_class, cli_runner):
        """Test chat with personality option."""
        mock_agent = MagicMock()
        mock_response = MagicMock()
        mock_response.message = "I'm in creative mode!"
        mock_response.confidence = 0.9
        mock_response.suggested_actions = ["Try asking for a story"]
        mock_agent.chat_sync.return_value = mock_response
        mock_agent_class.return_value = mock_agent
        
        with patch('rich.prompt.Prompt.ask', side_effect=['Tell me a story', 'exit']):
            result = cli_runner.invoke(cli, ['chat', '--personality', 'creative'])
            
            assert result.exit_code == 0
            assert "Suggested actions:" in result.output


class TestCodeCommands:
    """Test code generation and analysis commands."""
    
    @patch('src.agents.CodeAgent')
    def test_code_generate_basic(self, mock_agent_class, cli_runner):
        """Test basic code generation."""
        # Mock agent
        mock_agent = MagicMock()
        mock_response = MagicMock()
        mock_response.code = "def hello():\n    print('Hello, World!')"
        mock_response.language = "python"
        mock_response.framework = None
        mock_response.explanation = "A simple hello function"
        mock_response.dependencies = []
        mock_response.warnings = []
        mock_agent.generate_code_sync.return_value = mock_response
        mock_agent_class.return_value = mock_agent
        
        # Mock user inputs
        with patch('rich.prompt.Prompt.ask', side_effect=['Create a hello function', '']):
            with patch('questionary.text') as mock_text:
                mock_text.return_value.ask.return_value = 'Create a hello function'
                with patch('questionary.confirm') as mock_confirm:
                    mock_confirm.return_value.ask.return_value = False  # No requirements
                    
                    result = cli_runner.invoke(cli, ['code', 'generate', '-l', 'python'])
                    
                    assert result.exit_code == 0
                    assert "def hello():" in result.output
                    assert "Generated python code" in result.output
    
    @patch('src.agents.CodeAgent')
    def test_code_generate_with_output(self, mock_agent_class, cli_runner, temp_dir):
        """Test code generation with file output."""
        mock_agent = MagicMock()
        mock_response = MagicMock()
        mock_response.code = "console.log('test');"
        mock_response.language = "javascript"
        mock_response.framework = None
        mock_response.dependencies = ["none"]
        mock_response.warnings = []
        mock_agent.generate_code_sync.return_value = mock_response
        mock_agent_class.return_value = mock_agent
        
        output_file = temp_dir / "test.js"
        
        with patch('questionary.text') as mock_text:
            mock_text.return_value.ask.return_value = 'Log test'
            with patch('questionary.confirm') as mock_confirm:
                mock_confirm.return_value.ask.side_effect = [False, True]  # No requirements, yes save
                
                result = cli_runner.invoke(cli, [
                    'code', 'generate',
                    '-l', 'javascript',
                    '-o', str(output_file)
                ])
                
                assert result.exit_code == 0
                assert output_file.exists()
                assert output_file.read_text() == "console.log('test');"
    
    @patch('src.agents.AnalysisAgent')
    def test_code_analyze(self, mock_agent_class, cli_runner, temp_dir):
        """Test code analysis command."""
        # Create test file
        test_file = temp_dir / "test.py"
        test_file.write_text("def test():\n    pass")
        
        # Mock agent
        mock_agent = MagicMock()
        mock_response = MagicMock()
        mock_response.summary = "Code is clean and follows best practices"
        mock_response.issues = []
        mock_response.overall_score = 9.5
        mock_response.metrics = {"lines": 2, "complexity": 1}
        mock_response.suggestions = ["Add docstring"]
        mock_agent.analyze_code_sync.return_value = mock_response
        mock_agent_class.return_value = mock_agent
        
        result = cli_runner.invoke(cli, ['code', 'analyze', str(test_file)])
        
        assert result.exit_code == 0
        assert "Analysis Summary" in result.output
        assert "Overall Score: 9.5/10.0" in result.output
        assert "Add docstring" in result.output
    
    @patch('src.agents.AnalysisAgent')
    def test_code_analyze_with_issues(self, mock_agent_class, cli_runner, temp_dir):
        """Test code analysis with issues found."""
        test_file = temp_dir / "bad_code.py"
        test_file.write_text("password = 'hardcoded'")
        
        mock_agent = MagicMock()
        mock_response = MagicMock()
        mock_response.summary = "Security issues found"
        mock_response.issues = [
            MagicMock(
                type="security",
                severity="high",
                line_number=1,
                description="Hardcoded password"
            )
        ]
        mock_response.overall_score = 3.0
        mock_response.metrics = {}
        mock_response.suggestions = ["Use environment variables"]
        mock_agent.analyze_code_sync.return_value = mock_response
        mock_agent_class.return_value = mock_agent
        
        result = cli_runner.invoke(cli, [
            'code', 'analyze', str(test_file),
            '-t', 'security'
        ])
        
        assert result.exit_code == 0
        assert "Issues Found" in result.output
        assert "security" in result.output
        assert "high" in result.output


class TestMonitorCommand:
    """Test monitoring command functionality."""
    
    @patch('src.monitoring.create_monitoring_dashboard')
    def test_monitor_static(self, mock_dashboard, cli_runner):
        """Test static monitoring dashboard."""
        mock_dashboard.return_value = "Dashboard Layout"
        
        with patch('questionary.select') as mock_select:
            mock_select.return_value.ask.return_value = "❌ Exit"
            
            result = cli_runner.invoke(cli, ['monitor'])
            
            assert result.exit_code == 0
            assert "Available Metrics" in result.output
            mock_dashboard.assert_called_once()
    
    @patch('src.monitoring.live_monitoring_dashboard')
    @patch('asyncio.run')
    def test_monitor_live(self, mock_async_run, mock_live_dashboard, cli_runner):
        """Test live monitoring dashboard."""
        result = cli_runner.invoke(cli, ['monitor', '--live'])
        
        assert result.exit_code == 0
        assert "Starting live monitoring dashboard" in result.output
        mock_async_run.assert_called_once()
    
    @patch('src.monitoring.export_metrics')
    def test_monitor_export_json(self, mock_export, cli_runner, temp_dir):
        """Test metrics export as JSON."""
        mock_export.return_value = '{"metrics": "data"}'
        
        with cli_runner.isolated_filesystem(temp_dir=temp_dir):
            result = cli_runner.invoke(cli, ['monitor', '--export', 'json'])
            
            assert result.exit_code == 0
            assert "Metrics exported to" in result.output
            mock_export.assert_called_with(format='json')
            
            # Check file was created
            export_files = list(Path('.').glob('metrics_export_*.json'))
            assert len(export_files) == 1
            assert export_files[0].read_text() == '{"metrics": "data"}'
    
    @patch('src.monitoring.alert_manager')
    def test_monitor_alerts(self, mock_alert_manager, cli_runner):
        """Test alert checking."""
        mock_alert_manager.check_alerts.return_value = [
            {
                "severity": "high",
                "type": "error_rate",
                "message": "High error rate detected",
                "timestamp": "2024-01-01T00:00:00"
            }
        ]
        
        result = cli_runner.invoke(cli, ['monitor', '--alerts'])
        
        assert result.exit_code == 0
        assert "Active Alerts" in result.output
        assert "HIGH" in result.output
        assert "High error rate detected" in result.output


class TestConfigCommand:
    """Test configuration command."""
    
    def test_config_no_env_file(self, cli_runner, temp_dir):
        """Test config when no .env file exists."""
        with cli_runner.isolated_filesystem(temp_dir=temp_dir):
            with patch('rich.prompt.Confirm.ask', return_value=False):
                result = cli_runner.invoke(cli, ['config'])
                
                assert result.exit_code == 0
                assert "No .env file found" in result.output
    
    def test_config_create_from_example(self, cli_runner, temp_dir):
        """Test creating .env from example."""
        with cli_runner.isolated_filesystem(temp_dir=temp_dir):
            # Create example file
            example_file = Path(".env.example")
            example_file.write_text("OPENAI_API_KEY=your-key-here")
            
            with patch('rich.prompt.Confirm.ask', side_effect=[True, False]):
                result = cli_runner.invoke(cli, ['config'])
                
                assert result.exit_code == 0
                assert Path(".env").exists()
                assert Path(".env").read_text() == "OPENAI_API_KEY=your-key-here"
    
    @patch('subprocess.run')
    def test_config_open_editor(self, mock_subprocess, cli_runner, temp_dir):
        """Test opening .env in editor."""
        with cli_runner.isolated_filesystem(temp_dir=temp_dir):
            Path(".env").touch()
            
            with patch('rich.prompt.Confirm.ask', return_value=True):
                result = cli_runner.invoke(cli, ['config'])
                
                assert result.exit_code == 0
                mock_subprocess.assert_called_once()


class TestInteractiveMenu:
    """Test interactive menu functionality."""
    
    @patch('questionary.select')
    def test_menu_chat_selection(self, mock_select, cli_runner):
        """Test selecting chat from menu."""
        mock_select.return_value.ask.side_effect = [
            "💬 Chat - Interactive conversation with AI",
            "❌ Exit"
        ]
        
        with patch('src.cli.main.chat') as mock_chat:
            with patch('src.models.Settings'):
                result = cli_runner.invoke(cli, [])
                
                assert result.exit_code == 0
                mock_chat.invoke.assert_called_once()
    
    @patch('questionary.select')
    @patch('questionary.path')
    def test_menu_analyze_selection(self, mock_path, mock_select, cli_runner, temp_dir):
        """Test selecting code analysis from menu."""
        test_file = temp_dir / "test.py"
        test_file.write_text("print('test')")
        
        mock_select.return_value.ask.return_value = "🔍 Analyze Code - Review code for issues and improvements"
        mock_path.return_value.ask.return_value = str(test_file)
        
        with patch('src.cli.main.analyze_code') as mock_analyze:
            with patch('src.models.Settings'):
                result = cli_runner.invoke(cli, [])
                
                assert result.exit_code == 0
                mock_analyze.invoke.assert_called_once()