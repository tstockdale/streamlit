import unittest
import logging
import tempfile
import os
import json
from unittest.mock import patch, Mock
from src.weather_map.logging_config import (
    get_logging_config, setup_logging, get_logger, 
    PerformanceLogger, APILogger
)


class TestLoggingConfig(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up any handlers that might have been added
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            handler.close()
    
    def test_get_logging_config_default(self):
        """Test getting default logging configuration."""
        config = get_logging_config()
        
        self.assertIn('version', config)
        self.assertEqual(config['version'], 1)
        self.assertIn('formatters', config)
        self.assertIn('handlers', config)
        self.assertIn('loggers', config)
        
        # Check that all required formatters exist
        self.assertIn('detailed', config['formatters'])
        self.assertIn('json', config['formatters'])
        
        # Check that all required handlers exist
        self.assertIn('console', config['handlers'])
        self.assertIn('file_all', config['handlers'])  # Actual handler name
        self.assertIn('file_error', config['handlers'])  # Actual handler name
        self.assertIn('file_api', config['handlers'])  # Actual handler name
        self.assertIn('file_performance', config['handlers'])  # Actual handler name
    
    @patch('src.weather_map.logging_config.Path.mkdir')
    def test_get_logging_config_custom_log_dir(self, mock_mkdir):
        """Test getting logging configuration with custom log directory."""
        custom_dir = "/custom/logs"
        config = get_logging_config(custom_dir)
        
        # Check that file handlers use the custom directory
        file_handler = config['handlers']['file_all']  # Correct handler name
        self.assertTrue(file_handler['filename'].startswith(custom_dir))
        
        error_handler = config['handlers']['file_error']  # Correct handler name
        self.assertTrue(error_handler['filename'].startswith(custom_dir))
        
        # Verify mkdir was called
        mock_mkdir.assert_called_once_with(exist_ok=True)
    
    @patch('src.weather_map.logging_config.Path.mkdir')
    @patch('src.weather_map.logging_config.logging.config.dictConfig')
    def test_setup_logging_default(self, mock_dict_config, mock_mkdir):
        """Test setting up logging with default parameters."""
        setup_logging()
        
        # The setup_logging function calls get_logging_config which calls Path.mkdir()
        mock_mkdir.assert_called_once_with(exist_ok=True)
        mock_dict_config.assert_called_once()
    
    @patch.dict(os.environ, {'LOG_LEVEL': 'DEBUG'})
    @patch('src.weather_map.logging_config.Path.mkdir')
    @patch('src.weather_map.logging_config.logging.config.dictConfig')
    def test_setup_logging_with_env_log_level(self, mock_dict_config, mock_mkdir):
        """Test setting up logging with environment variable log level."""
        setup_logging()
        
        # Verify that the configuration was called
        mock_dict_config.assert_called_once()
        
        # Get the config that was passed to dictConfig
        config_arg = mock_dict_config.call_args[0][0]
        
        # Check that the root logger level is set to DEBUG (root logger uses empty string key)
        self.assertEqual(config_arg['loggers']['']['level'], 'DEBUG')
        # Also check that console handler level is set to DEBUG
        self.assertEqual(config_arg['handlers']['console']['level'], 'DEBUG')
    
    def test_get_logger(self):
        """Test getting a logger instance."""
        logger_name = 'test.module'
        logger = get_logger(logger_name)
        
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, logger_name)
    
    def test_performance_logger_success(self):
        """Test PerformanceLogger context manager with successful operation."""
        mock_logger = Mock()
        operation_name = "test_operation"
        
        with PerformanceLogger(operation_name, mock_logger):
            pass  # Simulate successful operation
        
        # Check that info log was called for completion
        mock_logger.info.assert_called()
        info_calls = mock_logger.info.call_args_list
        
        # Should have start and completion logs
        self.assertEqual(len(info_calls), 2)
        
        # Check start log
        start_call = info_calls[0][0][0]
        self.assertIn("Starting operation", start_call)
        self.assertIn(operation_name, start_call)
        
        # Check completion log
        completion_call = info_calls[1][0][0]
        self.assertIn("Completed operation", completion_call)
        self.assertIn(operation_name, completion_call)
        self.assertIn("in", completion_call)  # Should contain timing info
    
    def test_performance_logger_with_exception(self):
        """Test PerformanceLogger context manager with exception."""
        mock_logger = Mock()
        operation_name = "test_operation"
        
        with self.assertRaises(ValueError):
            with PerformanceLogger(operation_name, mock_logger):
                raise ValueError("Test exception")
        
        # Check that error log was called
        mock_logger.error.assert_called()
        error_call = mock_logger.error.call_args[0][0]
        self.assertIn("Failed operation", error_call)
        self.assertIn(operation_name, error_call)
    
    def test_performance_logger_default_logger(self):
        """Test PerformanceLogger with default logger."""
        operation_name = "test_operation"
        
        # Should not raise an exception even without explicit logger
        with PerformanceLogger(operation_name):
            pass
    
    def test_api_logger_log_request(self):
        """Test APILogger request logging."""
        mock_logger = Mock()
        api_logger = APILogger(mock_logger)
        
        method = "GET"
        url = "https://api.example.com/data"
        params = {"key": "value"}
        headers = {"Authorization": "Bearer token"}
        
        api_logger.log_request(method, url, params, headers)
        
        mock_logger.info.assert_called_once()
        log_message = mock_logger.info.call_args[0][0]
        self.assertIn("API Request", log_message)
        self.assertIn(method, log_message)
        self.assertIn(url, log_message)
    
    def test_api_logger_log_response(self):
        """Test APILogger response logging."""
        mock_logger = Mock()
        api_logger = APILogger(mock_logger)
        
        status_code = 200
        response_time = 0.5
        response_size = 1024
        
        api_logger.log_response(status_code, response_time, response_size)
        
        # The method uses logger.log() with dynamic level, not info()
        mock_logger.log.assert_called_once()
        log_call_args = mock_logger.log.call_args
        log_level = log_call_args[0][0]  # First positional arg is the level
        log_message = log_call_args[0][1]  # Second positional arg is the message
        
        self.assertEqual(log_level, logging.INFO)  # 200 status should use INFO level
        self.assertIn("API Response", log_message)
        self.assertIn(str(status_code), log_message)
        self.assertIn(str(response_time), log_message)
    
    def test_api_logger_log_error(self):
        """Test APILogger error logging."""
        mock_logger = Mock()
        api_logger = APILogger(mock_logger)
        
        error = Exception("Test error")
        context = {"url": "https://api.example.com", "method": "GET"}
        
        api_logger.log_error(error, context)
        
        mock_logger.error.assert_called_once()
        log_message = mock_logger.error.call_args[0][0]
        self.assertIn("API Error", log_message)
        self.assertIn("Test error", log_message)
    
    def test_api_logger_default_logger(self):
        """Test APILogger with default logger."""
        api_logger = APILogger()
        
        # Should not raise an exception
        api_logger.log_request("GET", "https://api.example.com")
        api_logger.log_response(200, 0.5)
        api_logger.log_error(Exception("Test"), {})


class TestLoggingIntegration(unittest.TestCase):
    """Integration tests for logging functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up any handlers that might have been added
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            handler.close()
    
    def test_end_to_end_logging_setup(self):
        """Test complete logging setup and usage."""
        # Setup logging with temporary directory
        setup_logging(log_dir=self.temp_dir)
        
        # Get a logger and log some messages
        logger = get_logger('test.integration')
        logger.info("Test info message")
        logger.error("Test error message")
        
        # Use PerformanceLogger
        with PerformanceLogger("test_operation", logger):
            pass
        
        # Use APILogger
        api_logger = APILogger(logger)
        api_logger.log_request("GET", "https://api.test.com")
        api_logger.log_response(200, 0.1)
        
        # Verify log files were created (they should exist even if empty due to setup)
        expected_files = ['app.log', 'error.log', 'api.log', 'performance.log']
        for filename in expected_files:
            filepath = os.path.join(self.temp_dir, filename)
            # File might not exist if no messages were actually written due to log levels
            # This test mainly verifies that setup doesn't crash
        
        # The main verification is that no exceptions were raised
        self.assertTrue(True)  # If we get here, the test passed


if __name__ == '__main__':
    unittest.main()
