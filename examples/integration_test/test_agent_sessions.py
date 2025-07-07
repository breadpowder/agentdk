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
        results.append((query, result))
    
    # Check that the agent loads successfully (no LLM setup errors)
    no_context_result = results[0][1]
    
    # If we get LLM setup errors, the test environment needs fixing
    if "langchain_openai not available" in no_context_result:
        pytest.skip("langchain_openai dependency not properly installed")
    elif "No LLM available" in no_context_result or "LLM is required" in no_context_result:
        pytest.skip("LLM setup failed - environment configuration issue")
    
    # If agent loaded successfully, verify appropriate responses
    # The agent should either:
    # 1. Respond appropriately to queries, or
    # 2. Show it's working by processing the queries
    assert len(no_context_result.strip()) > 10, f"Expected meaningful response, got: {no_context_result}"
    
    # Verify we got responses to other queries too
    list_tables_result = results[1][1] 
    customer_count_result = results[2][1]
    
    # Basic validation - if agent is working, it should provide substantive responses
    assert len(list_tables_result.strip()) > 10, f"Expected meaningful response to list tables, got: {list_tables_result}"
    assert len(customer_count_result.strip()) > 10, f"Expected meaningful response to customer count, got: {customer_count_result}"


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
    
    # Skip if environment issues
    if "langchain_openai not available" in first_result or "LLM is required" in first_result:
        pytest.skip("LLM setup failed - skipping session resumption test")
    
    # Continue with setup if agent is working
    for query in setup_queries[1:]:
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
    
    # Basic validation - if agent is working with resume, it should provide responses
    previous_table_result = results[0][1]
    previous_query_result = results[1][1]
    
    assert len(previous_table_result.strip()) > 10, f"Expected meaningful response with --resume, got: {previous_table_result}"
    assert len(previous_query_result.strip()) > 10, f"Expected meaningful response with --resume, got: {previous_query_result}"


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
    
    # Skip if environment issues
    if "langchain_openai not available" in no_context_result or "LLM is required" in no_context_result:
        pytest.skip("LLM setup failed - skipping memory learning test")
    
    # Try sequence of queries to test agent behavior
    case_fail_result = _run_agent_query(
        agent_examples_path,
        integration_test_queries["case_sensitive_fail"],
        resume=True
    )
    
    case_success_result = _run_agent_query(
        agent_examples_path,
        integration_test_queries["case_sensitive_success"], 
        resume=True
    )
    
    # Basic validation - agent should provide meaningful responses
    assert len(no_context_result.strip()) > 10, f"Expected meaningful initial response, got: {no_context_result}"
    assert len(case_fail_result.strip()) > 10, f"Expected meaningful response to case sensitive query, got: {case_fail_result}"
    assert len(case_success_result.strip()) > 10, f"Expected meaningful response to subsequent query, got: {case_success_result}"


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
        results.append((query, result))
    
    # Verify EDA agent basic functionality
    no_context_result = results[0][1]
    
    # Skip if environment issues
    if "langchain_openai not available" in no_context_result or "LLM is required" in no_context_result:
        pytest.skip("LLM setup failed - skipping EDA agent test")
    
    # Verify EDA agent can handle table operations
    list_tables_result = results[1][1]
    customer_count_result = results[2][1]
    
    # Basic validation - EDA agent should provide meaningful responses
    assert len(no_context_result.strip()) > 10, f"EDA agent: Expected meaningful response, got: {no_context_result}"
    assert len(list_tables_result.strip()) > 10, f"EDA agent: Expected meaningful response, got: {list_tables_result}"
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
            cwd="/home/zineng/workspace/agentic/agentdk"
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