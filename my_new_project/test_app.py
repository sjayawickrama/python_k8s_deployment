import pytest
# Use 'mock' for installation, but import it from unittest.mock for Python 3.3+
import unittest.mock as mock 
import app as flask_app_module 
import os
import time

# --- FIXTURES ---

@pytest.fixture
def flask_app():
    """A pytest fixture that creates a test client using the app factory and mock config."""
    
    # 1. Define the test configuration, including the mocked DB_HOST
    test_config = {
        'DB_HOST': 'mock_db',
        'DB_USER': 'user',
        'DB_PASSWORD': 'password',
        'DB_NAME': 'testdb'
    }
    
    # 2. Call the factory function from app.py, passing the test config
    app_instance = flask_app_module.create_app(test_config=test_config)
    
    # The factory function sets app_instance.testing = True automatically
    
    # 3. Use the test client
    with app_instance.test_client() as client:
        yield client

# --- TEST FUNCTIONS ---

def test_index_route(flask_app):
    """Test the main index page (GET) loads correctly and uses the mocked DB host."""
    
    response = flask_app.get('/')
    assert response.status_code == 200
    
    # This assertion now passes because the template content is restored and the DB host is mocked
    assert b"Kubernetes Login Demo" in response.data 
    assert b"DB Host Check: mock_db" in response.data


# Mocking the database connection and time.sleep is essential for unit tests
@mock.patch('app.mysql.connector.connect')
@mock.patch('app.time.sleep')
def test_wait_for_db_and_initialize_success(mock_sleep, mock_connect):
    """Test the retry mechanism succeeds on the first attempt."""
    
    # Dummy app config to pass to the function (the function expects a dictionary)
    app_config = {'DB_HOST': 'mock_db', 'DB_USER': 'user', 'DB_PASSWORD': 'password', 'DB_NAME': 'testdb'}

    # Patch initialize_database to return True immediately (success)
    with mock.patch('app.initialize_database', return_value=True) as mock_init:
        # Call the function using the correct module alias and passing the config
        flask_app_module.wait_for_db_and_initialize(app_config, max_retries=3)
    
    mock_init.assert_called_once_with(app_config)
    mock_sleep.assert_not_called()

# Mocking the database connection and time.sleep
@mock.patch('app.mysql.connector.connect')
@mock.patch('app.time.sleep')
def test_wait_for_db_and_initialize_retries(mock_sleep, mock_connect):
    """Test the retry mechanism successfully connects after a failure."""
    
    # Dummy app config to pass to the function
    app_config = {'DB_HOST': 'mock_db', 'DB_USER': 'user', 'DB_PASSWORD': 'password', 'DB_NAME': 'testdb'}

    # Mock initialize_database to fail once (False), then succeed (True)
    mock_init = mock.MagicMock(side_effect=[False, True])
    
    with mock.patch('app.initialize_database', mock_init):
        # Call the function using the correct module alias and passing the config
        flask_app_module.wait_for_db_and_initialize(app_config, max_retries=3, delay_seconds=1)
        
    assert mock_init.call_count == 2
    mock_sleep.assert_called_once_with(1)

# You would add more tests here for the /login route, create_db_connection, etc.
