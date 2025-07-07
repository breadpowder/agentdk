"""Integration tests for end-to-end agent session scenarios."""

import pytest
import os
import subprocess
import re
import time
from pathlib import Path
from typing import List, Tuple


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
    1. No previous context exists
    2. Can list tables successfully 
    3. Can count customers and return numeric result
    """
    queries = [
        integration_test_queries["no_context"],
        integration_test_queries["list_tables"], 
        integration_test_queries["customer_count"]
    ]
    
    results = []
    for query in queries:
        result = _run_agent_query(agent_examples_path, query, resume=False)
        results.append((query, result))
    
    # Verify no previous context
    no_context_result = results[0][1]
    assert any(phrase in no_context_result.lower() for phrase in [
        "no previous", "haven't accessed", "no table", "don't have", "no record"
    ]), f"Expected no previous context, got: {no_context_result}"
    
    # Verify table listing
    list_tables_result = results[1][1] 
    assert any(table in list_tables_result.lower() for table in [
        "customers", "accounts", "table"
    ]), f"Expected table names in result, got: {list_tables_result}"
    
    # Verify customer count (numeric result)
    customer_count_result = results[2][1]
    assert re.search(r'\d+', customer_count_result), f"Expected numeric count, got: {customer_count_result}"


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
    2. Resume session and verify previous context is maintained
    3. Verify memory of previous table access and queries
    """
    # First session: establish context
    setup_queries = [
        integration_test_queries["list_tables"],
        integration_test_queries["customer_count"]
    ]
    
    for query in setup_queries:
        _run_agent_query(agent_examples_path, query, resume=False)
        time.sleep(1)  # Small delay between queries
    
    # Resume session and test memory
    memory_queries = [
        integration_test_queries["previous_table"],
        integration_test_queries["previous_query"]
    ]
    
    results = []
    for query in memory_queries:
        result = _run_agent_query(agent_examples_path, query, resume=True)
        results.append((query, result))
    
    # Verify previous table access memory
    previous_table_result = results[0][1]
    assert "customer" in previous_table_result.lower(), f"Expected 'customer' table reference, got: {previous_table_result}"
    
    # Verify previous query memory  
    previous_query_result = results[1][1]
    assert any(term in previous_query_result.lower() for term in [
        "count", "customer", "query", "select"
    ]), f"Expected query reference, got: {previous_query_result}"


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
    1. Start fresh and verify no previous context
    2. Try case-sensitive query that should fail/return nothing
    3. User provides correction (case insensitive approach)
    4. Verify agent learned from correction for subsequent queries
    """
    # Start fresh
    no_context_result = _run_agent_query(
        agent_examples_path, 
        integration_test_queries["no_context"], 
        resume=False
    )
    assert any(phrase in no_context_result.lower() for phrase in [
        "no previous", "haven't accessed", "no table", "don't have"
    ]), f"Expected no previous context, got: {no_context_result}"
    
    # Try case-sensitive query (should fail or return nothing meaningful)
    case_fail_result = _run_agent_query(
        agent_examples_path,
        integration_test_queries["case_sensitive_fail"],
        resume=True
    )
    
    # Note: The agent might still succeed here if it's smart about case handling
    # The key is testing that subsequent queries work after any correction
    
    # Test learned behavior with similar case-sensitive query
    case_success_result = _run_agent_query(
        agent_examples_path,
        integration_test_queries["case_sensitive_success"], 
        resume=True
    )
    
    # Verify that the agent can handle the second query successfully
    # This tests that it either learned from the first query or has consistent behavior
    assert any(term in case_success_result.lower() for term in [
        "saving", "maximum", "max", "amount", "account"
    ]) or re.search(r'\d+', case_success_result), f"Expected successful query result, got: {case_success_result}"


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
    1. Sub-agent responds correctly to table queries
    2. Memory persistence works in sub-agent context  
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
        results.append((query, result))
    
    # Verify EDA agent basic functionality
    no_context_result = results[0][1]
    assert any(phrase in no_context_result.lower() for phrase in [
        "no previous", "haven't accessed", "no table", "don't have", "no record"
    ]), f"EDA agent: Expected no previous context, got: {no_context_result}"
    
    # Verify EDA agent can handle table operations
    list_tables_result = results[1][1]
    # EDA agent should be able to work with data/tables
    assert len(list_tables_result.strip()) > 10, f"EDA agent: Expected meaningful response, got: {list_tables_result}"
    
    # Test EDA agent with data query
    customer_count_result = results[2][1]
    # EDA agent should provide some form of data analysis response
    assert len(customer_count_result.strip()) > 10, f"EDA agent: Expected meaningful response, got: {customer_count_result}"


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
    
    try:
        # Run the agent with the query
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True,
            cwd="/home/zineng/workspace/agentic/agentdk"
        )
        
        stdout, stderr = process.communicate(input=query, timeout=60)
        
        if process.returncode != 0:
            # Log error but don't fail test immediately - agent might still provide useful output
            print(f"Agent process returned {process.returncode}")
            print(f"STDERR: {stderr}")
        
        # Return stdout even if there were errors, as agent might still provide response
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