"""Integration tests for end-to-end agent session scenarios."""

import pytest
import os
import subprocess
import re
import time
import logging
from pathlib import Path
from typing import List, Tuple

# Configure logger for integration tests
logger = logging.getLogger(__name__)


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
def test_fresh_agent_session(
    openai_api_key, 
    agent_examples_path, 
    clean_session_environment,
    integration_test_queries
):
    """Test fresh agent session start without prior context.
    
    Scenario: Start agent from fresh state and verify:
    1. Agent loads successfully with LLM
    2. Can handle queries appropriately
    3. Shows appropriate responses or error handling
    """
    queries = [
        integration_test_queries["no_context"],
        integration_test_queries["list_tables"], 
        integration_test_queries["customer_count"]
    ]
    
    results = []
    for query in queries:
        result = _run_agent_query(agent_examples_path, query, resume=False)
        logger.info(f"Agent response for query '{query}': {result}")
        results.append((query, result))
    
    # Check that the agent loads successfully (no LLM setup errors)
    no_context_result = results[0][1]
    
    # If we get LLM setup errors, the test environment needs fixing
    if "langchain_openai not available" in no_context_result:
        pytest.skip("langchain_openai dependency not properly installed")
    elif "No LLM available" in no_context_result or "LLM is required" in no_context_result:
        pytest.skip("LLM setup failed - environment configuration issue")
    
    # Verify appropriate responses using helper functions
    list_tables_result = results[1][1] 
    customer_count_result = results[2][1]
    
    # Verify agent loads successfully and provides meaningful responses
    assert len(no_context_result.strip()) > 10, f"Expected meaningful response, got: {no_context_result}"
    
    # Verify list tables response contains expected table names
    table_keywords = ["tables", "accounts", "customers", "transactions"]
    assert _verify_output_contains_keywords(list_tables_result, table_keywords), \
        f"Expected table-related response with keywords {table_keywords}, got: {list_tables_result}"
    
    # Verify customer count response contains numeric value
    customer_numbers = _extract_numeric_values(customer_count_result)
    assert len(customer_numbers) > 0, f"Expected numeric customer count, got: {customer_count_result}"
    assert any(num > 0 for num in customer_numbers), f"Expected positive customer count, got: {customer_numbers}"
    
    # Verify customer count response contains relevant keywords
    count_keywords = ["customers", "total", "count"]
    assert _verify_output_contains_keywords(customer_count_result, count_keywords), \
        f"Expected customer count response with keywords {count_keywords}, got: {customer_count_result}"


@pytest.mark.integration  
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
def test_session_resumption(
    openai_api_key,
    agent_examples_path, 
    clean_session_environment,
    integration_test_queries
):
    """Test session resumption with --resume flag.
    
    Scenario: 
    1. Run initial queries to establish context
    2. Resume session and verify agent handles resume appropriately
    3. Test that --resume flag is processed correctly
    """
    # First session: establish context
    setup_queries = [
        integration_test_queries["list_tables"],
        integration_test_queries["customer_count"]
    ]
    
    # Run setup queries and check if agent works
    first_result = _run_agent_query(agent_examples_path, setup_queries[0], resume=False)
    logger.info(f"Initial setup query response: {first_result}")
    
    # Skip if environment issues
    if "langchain_openai not available" in first_result or "LLM is required" in first_result:
        pytest.skip("LLM setup failed - skipping session resumption test")
    
    # Continue with setup if agent is working
    for query in setup_queries[1:]:
        setup_result = _run_agent_query(agent_examples_path, query, resume=False)
        logger.info(f"Setup query response for '{query}': {setup_result}")
        time.sleep(1)  # Small delay between queries
    
    # Resume session and test memory
    memory_queries = [
        integration_test_queries["previous_table"],
        integration_test_queries["previous_query"]
    ]
    
    results = []
    for query in memory_queries:
        result = _run_agent_query(agent_examples_path, query, resume=True)
        logger.info(f"Agent response for query '{query}' (resume=True): {result}")
        results.append((query, result))
    
    # Verify session resumption responses using helper functions
    previous_table_result = results[0][1]
    previous_query_result = results[1][1]
    
    # Basic validation - responses should be meaningful
    assert len(previous_table_result.strip()) > 10, f"Expected meaningful response with --resume, got: {previous_table_result}"
    assert len(previous_query_result.strip()) > 10, f"Expected meaningful response with --resume, got: {previous_query_result}"
    
    # Verify memory-related responses contain relevant keywords
    memory_keywords = ["table", "query", "previous", "accessed", "customers", "accounts"]
    assert _verify_output_contains_keywords(previous_table_result, memory_keywords), \
        f"Expected memory-aware response with keywords {memory_keywords}, got: {previous_table_result}"
    assert _verify_output_contains_keywords(previous_query_result, memory_keywords), \
        f"Expected memory-aware response with keywords {memory_keywords}, got: {previous_query_result}"


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
def test_memory_learning_correction(
    openai_api_key,
    agent_examples_path,
    clean_session_environment, 
    integration_test_queries
):
    """Test memory learning and user correction scenarios.
    
    Scenario:
    1. Start fresh and verify agent handles queries
    2. Test multiple queries in sequence
    3. Verify agent processes queries consistently
    """
    # Start fresh
    no_context_result = _run_agent_query(
        agent_examples_path, 
        integration_test_queries["no_context"], 
        resume=False
    )
    logger.info(f"No context query response: {no_context_result}")
    
    # Skip if environment issues
    if "langchain_openai not available" in no_context_result or "LLM is required" in no_context_result:
        pytest.skip("LLM setup failed - skipping memory learning test")
    
    # Try sequence of queries to test agent behavior
    case_fail_result = _run_agent_query(
        agent_examples_path,
        integration_test_queries["case_sensitive_fail"],
        resume=True
    )
    logger.info(f"Case sensitive fail query response: {case_fail_result}")
    
    case_success_result = _run_agent_query(
        agent_examples_path,
        integration_test_queries["case_sensitive_success"], 
        resume=True
    )
    logger.info(f"Case sensitive success query response: {case_success_result}")
    
    # Verify memory learning responses using helper functions
    assert len(no_context_result.strip()) > 10, f"Expected meaningful initial response, got: {no_context_result}"
    assert len(case_fail_result.strip()) > 10, f"Expected meaningful response to case sensitive query, got: {case_fail_result}"
    assert len(case_success_result.strip()) > 10, f"Expected meaningful response to subsequent query, got: {case_success_result}"
    
    # Verify case-sensitive queries contain relevant keywords
    account_keywords = ["account", "amount", "average", "max", "saving", "chequing"]
    assert _verify_output_contains_keywords(case_fail_result, account_keywords), \
        f"Expected account-related response with keywords {account_keywords}, got: {case_fail_result}"
    assert _verify_output_contains_keywords(case_success_result, account_keywords), \
        f"Expected account-related response with keywords {account_keywords}, got: {case_success_result}"
    
    # Extract numeric values from account queries (amounts, averages, etc.)
    case_fail_numbers = _extract_numeric_values(case_fail_result)
    case_success_numbers = _extract_numeric_values(case_success_result)
    
    # At least one query should contain numeric results (amounts, counts, etc.)
    assert len(case_fail_numbers) > 0 or len(case_success_numbers) > 0, \
        f"Expected numeric values in account queries. Fail: {case_fail_numbers}, Success: {case_success_numbers}"


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set") 
def test_subagent_functionality(
    openai_api_key,
    eda_agent_path,
    clean_session_environment,
    integration_test_queries
):
    """Test EDA sub-agent with same scenarios.
    
    Scenario: Run same basic tests with EDA agent to verify:
    1. Sub-agent loads and responds correctly
    2. EDA agent processes queries appropriately  
    3. EDA-specific functionality operates properly
    """
    # Test basic functionality with EDA agent
    queries = [
        integration_test_queries["no_context"],
        integration_test_queries["list_tables"], 
        integration_test_queries["customer_count"]
    ]
    
    results = []
    for query in queries:
        result = _run_agent_query(eda_agent_path, query, resume=False)
        logger.info(f"EDA agent response for query '{query}': {result}")
        results.append((query, result))
    
    # Verify EDA agent basic functionality
    no_context_result = results[0][1]
    
    # Skip if environment issues
    if "langchain_openai not available" in no_context_result or "LLM is required" in no_context_result:
        pytest.skip("LLM setup failed - skipping EDA agent test")
    
    # Verify EDA agent can handle table operations
    list_tables_result = results[1][1]
    customer_count_result = results[2][1]
    
    # Verify EDA agent responses using helper functions
    assert len(no_context_result.strip()) > 10, f"EDA agent: Expected meaningful response, got: {no_context_result}"
    assert len(list_tables_result.strip()) > 10, f"EDA agent: Expected meaningful response, got: {list_tables_result}"
    assert len(customer_count_result.strip()) > 10, f"EDA agent: Expected meaningful response, got: {customer_count_result}"
    
    # Verify EDA agent provides table-related responses
    table_keywords = ["tables", "accounts", "customers", "transactions"]
    assert _verify_output_contains_keywords(list_tables_result, table_keywords), \
        f"EDA agent: Expected table-related response with keywords {table_keywords}, got: {list_tables_result}"
    
    # Verify EDA agent provides customer count with numeric values
    customer_numbers = _extract_numeric_values(customer_count_result)
    assert len(customer_numbers) > 0, f"EDA agent: Expected numeric customer count, got: {customer_count_result}"
    assert any(num > 0 for num in customer_numbers), f"EDA agent: Expected positive customer count, got: {customer_numbers}"
    
    # Verify EDA agent uses appropriate keywords
    count_keywords = ["customers", "total", "count"]
    assert _verify_output_contains_keywords(customer_count_result, count_keywords), \
        f"EDA agent: Expected customer count response with keywords {count_keywords}, got: {customer_count_result}"


def _run_agent_query(agent_path: str, query: str, resume: bool = False) -> str:
    """Helper function to run agent query and return result.
    
    Args:
        agent_path: Path to agent file (e.g., "examples/agent_app.py")
        query: Query string to send to agent
        resume: Whether to use --resume flag
        
    Returns:
        Agent response as string
    """
    cmd = ["uv", "run", "python", "-m", "agentdk.cli.main", "run", agent_path]
    if resume:
        cmd.append("--resume")
    
    # Ensure environment variables are passed to subprocess
    env = os.environ.copy()
    
    try:
        # Run the agent with the query
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True,
            env=env,  # Pass environment variables
            cwd=Path(__file__).parent.parent.parent  # Navigate to repository root
        )
        
        stdout, stderr = process.communicate(input=query, timeout=60)
        
        if process.returncode != 0:
            # Log error but don't fail test immediately - agent might still provide useful output
            print(f"Agent process returned {process.returncode}")
            print(f"STDERR: {stderr}")
            # Return stderr + stdout for analysis as the agent may provide error information
            return f"{stderr}\n{stdout}".strip()
        
        # Return stdout for successful runs
        return stdout.strip()
        
    except subprocess.TimeoutExpired:
        process.kill()
        raise TimeoutError(f"Agent query timed out: {query}")
    except Exception as e:
        raise RuntimeError(f"Failed to run agent query '{query}': {e}")


def _verify_output_contains_keywords(output: str, keywords: List[str]) -> bool:
    """Helper to verify output contains any of the expected keywords."""
    output_lower = output.lower()
    return any(keyword.lower() in output_lower for keyword in keywords)


def _extract_numeric_values(text: str) -> List[int]:
    """Helper to extract numeric values from text."""
    return [int(match.group()) for match in re.finditer(r'\d+', text)]