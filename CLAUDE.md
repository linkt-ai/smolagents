# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`smolagents` is a lightweight library for building AI agents that can execute Python code and use tools. The core philosophy is simplicity: the main agent logic fits in ~1,000 lines of code in `agents.py`. The library supports two primary agent types:

- **CodeAgent**: Agents that write their actions as executable Python code (recommended approach - 30% more efficient than traditional tool calling)
- **ToolCallingAgent**: Traditional agents that output JSON/text tool calls

## Development Commands

### Installation
```bash
# Install with dev dependencies (using pip)
pip install -e ".[dev]"

# OR using uv
uv pip install -e "smolagents[dev] @ ."

# Install with specific extras for development
pip install -e ".[all]"  # All optional dependencies
```

### Code Quality
```bash
make quality      # Check code quality (ruff check + format check)
make style        # Auto-format code (ruff check --fix + format)
```

### Testing
```bash
make test                    # Run all tests
pytest ./tests/              # Run all tests (explicit)
pytest ./tests/test_agents.py  # Run specific test file
pytest ./tests/test_agents.py::TestCodeAgent  # Run specific test class
pytest ./tests/test_agents.py::TestCodeAgent::test_run  # Run specific test
pytest -v                    # Verbose output
pytest -k "pattern"          # Run tests matching pattern
```

### CLI Commands
```bash
# Run agent interactively (setup wizard)
smolagent

# Run agent with direct prompt
smolagent "Your task here" --model-type "InferenceClientModel" --model-id "Qwen/Qwen3-Next-80B-A3B-Thinking" --tools web_search

# Web browsing agent using helium
webagent "Navigate to example.com and extract product details" --model-type "LiteLLMModel" --model-id "gpt-4"
```

## Architecture

### Core Components

**agents.py** (~1,000 LOC - the heart of the library)
- `Agent` (abstract base class)
- `CodeAgent`: Executes actions as Python code snippets
- `ToolCallingAgent`: Traditional tool calling with JSON outputs
- `MultiStepAgent`: Manages multi-step ReAct loops
- `ManagedAgent`: Agent that can be managed by other agents

**tools.py**
- `BaseTool` (abstract interface)
- `Tool` (main implementation): Defines callable functions for agents
- `ToolCollection`: Manages groups of tools
- Tool loading: `Tool.from_hub()`, `Tool.from_space()`, `Tool.from_langchain()`, `ToolCollection.from_mcp()`

**models.py**
- `Model` (abstract base class)/
- Model implementations: `InferenceClientModel`, `OpenAIModel`, `LiteLLMModel`, `TransformersModel`, `AzureOpenAIModel`, `AmazonBedrockModel`, `MLXModel`, `VLLMModel`
- `ChatMessage`, `ChatMessageToolCall`: Message structures
- `MessageRole`: Enum for message roles (USER, ASSISTANT, SYSTEM, TOOL_CALL, TOOL_RESPONSE)

**Execution Engines**

*local_python_executor.py*
- `LocalPythonExecutor`: Secure Python interpreter with restricted operations
- `PythonExecutor` (abstract base): Interface for code execution
- Implements safety features: operation limits, dunder method restrictions, import controls

*remote_executors.py*
- `BlaxelExecutor`: Remote execution via Blaxel sandboxes
- `E2BExecutor`: Remote execution via E2B
- `ModalExecutor`: Remote execution via Modal
- `DockerExecutor`: Docker container execution
- `WasmExecutor`: WebAssembly sandbox (Pyodide + Deno)

**memory.py**
- `AgentMemory`: Manages conversation history and agent state
- Memory step types: `ActionStep`, `TaskStep`, `SystemPromptStep`, `PlanningStep`, `FinalAnswerStep`
- `ToolCall`: Represents tool invocation records
- `CallbackRegistry`: Event-based hooks for agent lifecycle

**agent_types.py**
- `AgentType`: Base class for agent-returnable types
- `AgentText`, `AgentImage`, `AgentAudio`: Multimodal output types
- Type handling utilities: `handle_agent_input_types()`, `handle_agent_output_types()`

### Key Abstractions

**Agent Loop (ReAct Pattern)**
```
User Task → AgentMemory
          ↓
    ┌─────────────────┐
    │  ReAct Loop     │
    │  1. Memory →    │
    │  2. Model Gen → │
    │  3. Parse Code →│
    │  4. Execute →   │
    │  5. Store Logs →│
    └─────────────────┘
          ↓
    final_answer() called → Return Result
```

**Tool Definition Pattern**
Tools must define:
- `name`: String identifier (used in generated code)
- `description`: Natural language description
- `inputs`: Dict mapping parameter names to type/description
- `output_type`: Expected return type
- `forward()`: Implementation method

**Prompt Templates**
Located in `src/smolagents/prompts/`:
- `code_agent.yaml`: Prompts for CodeAgent
- `structured_code_agent.yaml`: Structured output variant
- `toolcalling_agent.yaml`: Prompts for ToolCallingAgent

Templates use Jinja2 and are populated via `populate_template()` in agents.py.

### Security Model

Code execution security is critical. The library provides multiple isolation levels:

1. **LocalPythonExecutor** (default): Restricted Python interpreter
   - Limits operations (MAX_OPERATIONS = 10,000,000)
   - Blocks dunder attribute access (except `__init__`, `__str__`, `__repr__`)
   - Controls imports via `BASE_BUILTIN_MODULES` and `additional_authorized_imports`
   - No file system access by default

2. **Remote Executors**: Full sandboxing
   - Blaxel, E2B, Modal: Cloud-based sandboxes
   - Docker: Container isolation
   - Wasm: Browser-based isolation (Pyodide + Deno)

3. **Import Control**: `additional_authorized_imports` parameter allows specific packages

### Hub Integration

Tools and agents can be shared via HuggingFace Hub:
```python
# Share to Hub
agent.push_to_hub("username/agent-name")
tool.push_to_hub("username/tool-name")

# Load from Hub
agent = Agent.from_hub("username/agent-name")
tool = Tool.from_hub("username/tool-name")
```

## Common Development Patterns

### Creating a Custom Tool

```python
from smolagents import Tool

class MyTool(Tool):
    name = "my_tool"
    description = "Description of what the tool does"
    inputs = {
        "param1": {"type": "string", "description": "First parameter"},
    }
    output_type = "string"

    def forward(self, param1: str) -> str:
        # Implementation
        return result
```

### Running Tests for Specific Components

Tests are organized by component:
- `test_agents.py`: Agent behavior tests (largest file ~103KB)
- `test_local_python_executor.py`: Executor security tests (~99KB)
- `test_tools.py`: Tool functionality tests
- `test_models.py`: Model integration tests (~41KB)
- `test_gradio_ui.py`: Gradio interface tests
- `test_memory.py`: Memory system tests
- `test_mcp_client.py`: MCP integration tests

### Error Handling

The library defines specific exception types in `utils.py`:
- `AgentError` (base)
- `AgentExecutionError`: Code execution failures
- `AgentGenerationError`: LLM generation failures
- `AgentParsingError`: Output parsing failures
- `AgentToolCallError`: Tool invocation errors
- `AgentToolExecutionError`: Tool execution errors
- `AgentMaxStepsError`: Exceeded iteration limit

### Monitoring and Logging

The monitoring system (`monitoring.py`) provides:
- `AgentLogger`: Structured logging for agent actions
- `Monitor`: Observability hooks
- `LogLevel`: NONE, INNER_THOUGHTS, AGENTS_ACTIONS, TOOL_LOGS
- OpenTelemetry integration for tracing (via `telemetry` extra)

### Working with Multimodal Inputs

Agents support text, images, video, and audio:
```python
# Image inputs are automatically handled
agent.run("Analyze this image", image=AgentImage("path/to/image.png"))

# Audio inputs
agent.run("Transcribe this", audio=AgentAudio("path/to/audio.wav"))
```

## Testing Philosophy

- Tests use pytest fixtures defined in `conftest.py`
- Mock LLM responses for unit tests (avoid real API calls)
- `test_all_docs.py` validates documentation examples
- Use `@pytest.mark.timeout` for tests that may hang
- Test data stored in `tests/fixtures/` (loaded via pytest-datadir)

## Code Style

- Line length: 119 characters (configured in pyproject.toml)
- Ruff for linting and formatting
- Import order: standard library, third-party, smolagents modules
- Two blank lines after imports (enforced by ruff isort config)
- Ignore patterns: F403 (star imports), E501 (line length)

## Important Implementation Details

1. **Final Answer Handling**: The `final_answer()` tool must be called to return results. In remote executors, this is patched to raise a `FinalAnswerException` to halt execution.

2. **Code Action Format**: CodeAgent expects actions as Python code blocks. The parser extracts code using regex patterns defined in `utils.py:parse_code_blobs()`.

3. **Tool Validation**: Tool arguments are validated via `tool_validation.py:validate_tool_arguments()` before execution.

4. **Streaming**: Both agents and models support streaming via `stream_outputs=True`. Stream deltas are agglomerated using `agglomerate_stream_deltas()`.

5. **SyntaxError Format**: Keep exception type and message on same line when raising SyntaxError (see commit e7b402c).

6. **Response Format**: CodeAgent uses structured JSON output via `CODEAGENT_RESPONSE_FORMAT` with fields `thought` and `code`.
