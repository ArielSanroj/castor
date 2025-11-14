"""
Tests for caching functionality.
"""
import pytest
from unittest.mock import patch, Mock
from utils.cache import init_cache, get, set, get_cache_key, cached


def test_cache_key_generation():
    """Test cache key generation."""
    key1 = get_cache_key("test", "arg1", "arg2", kwarg1="value1")
    key2 = get_cache_key("test", "arg1", "arg2", kwarg1="value1")
    key3 = get_cache_key("test", "arg1", "arg2", kwarg1="value2")
    
    # Same args should generate same key
    assert key1 == key2
    # Different args should generate different key
    assert key1 != key3
    # Should have prefix
    assert key1.startswith("castor:test:")


def test_cache_set_get():
    """Test basic cache set and get."""
    init_cache()
    
    test_key = "test:key:123"
    test_value = {"data": "test"}
    
    set(test_key, test_value, ttl=60)
    result = get(test_key)
    
    assert result == test_value


@patch('utils.cache.redis_client')
def test_cache_with_redis(mock_redis):
    """Test cache with Redis."""
    # Mock Redis client
    mock_redis_instance = Mock()
    mock_redis_instance.ping.return_value = True
    mock_redis_instance.get.return_value = '{"cached": "data"}'
    mock_redis_instance.setex = Mock()
    mock_redis.from_url.return_value = mock_redis_instance
    
    init_cache()
    
    test_key = "test:key"
    test_value = {"cached": "data"}
    
    result = get(test_key)
    assert result == test_value


def test_cached_decorator():
    """Test cached decorator."""
    init_cache()
    
    call_count = [0]
    
    @cached("test_func", ttl=60)
    def test_function(x, y):
        call_count[0] += 1
        return x + y
    
    # First call should execute function
    result1 = test_function(1, 2)
    assert result1 == 3
    assert call_count[0] == 1
    
    # Second call should use cache
    result2 = test_function(1, 2)
    assert result2 == 3
    assert call_count[0] == 1  # Should not increment
    
    # Different args should execute again
    result3 = test_function(2, 3)
    assert result3 == 5
    assert call_count[0] == 2

