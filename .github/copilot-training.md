# Copilot Training Data — Greybeard

## Code Patterns

### Analyzer Pattern
```python
from greybeard.models import ReviewRequest, ContentPack
from greybeard.analyzer import run_review
from greybeard.config import GreybeardConfig

# Create review request
pack = ContentPack(
    name="staff-core",
    perspective="Senior Engineer",
    tone="direct"
)
req = ReviewRequest(
    mode="review",
    pack=pack,
    input_text="code to review",
    context_notes="any extra context"
)

# Get config (from file or dict)
config = GreybeardConfig.load()  # or .from_dict({...})

# Run review
result = run_review(req, config=config)
print(result)

# Async version for FastAPI
async def review_api(req: ReviewRequest):
    result = await run_review_async(req)
    return result
```

### CLI Command Pattern
```python
# greybeard/cli.py
import click
from greybeard.analyzer import run_review

@click.command()
@click.argument('input_file', type=click.File('r'))
@click.option('--mode', default='review', help='Review mode')
@click.option('--pack', default='staff-core', help='Content pack')
@click.option('--backend', default='openai', help='LLM backend')
def analyze(input_file, mode, pack, backend):
    """Analyze code or documentation."""
    content = input_file.read()
    
    req = ReviewRequest(
        mode=mode,
        pack=ContentPack.load(pack),
        input_text=content
    )
    
    config = GreybeardConfig.load()
    config.llm.backend = backend
    
    result = run_review(req, config=config)
    click.echo(result)
```

### Backend Implementation
```python
# greybeard/backends/custom_backend.py
from typing import Optional
from .base import Backend, BackendResponse

class CustomBackend(Backend):
    """Custom LLM backend implementation."""
    
    def __init__(self, config: dict):
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url")
        self.model = config.get("model", "default-model")
    
    def call(
        self,
        system_prompt: str,
        user_message: str,
        stream: bool = False,
        **kwargs
    ) -> BackendResponse:
        """Call the LLM synchronously."""
        try:
            response = self._call_api(
                system_prompt=system_prompt,
                message=user_message,
                stream=stream
            )
            
            return BackendResponse(
                text=response.get("text"),
                input_tokens=response.get("input_tokens", 0),
                output_tokens=response.get("output_tokens", 0)
            )
        except Exception as e:
            raise RuntimeError(f"Backend error: {e}")
    
    def _call_api(self, **kwargs) -> dict:
        """Make actual API call."""
        import requests
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": kwargs.get("system_prompt")},
                {"role": "user", "content": kwargs.get("message")}
            ]
        }
        
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json=payload,
            headers=headers
        )
        response.raise_for_status()
        
        data = response.json()
        return {
            "text": data["choices"][0]["message"]["content"],
            "input_tokens": data.get("usage", {}).get("prompt_tokens", 0),
            "output_tokens": data.get("usage", {}).get("completion_tokens", 0)
        }
```

### Pack Pattern
```python
# Custom content pack
from greybeard.packs import ContentPack

pack = ContentPack(
    name="my-security-pack",
    perspective="Security Engineer",
    tone="technical",
    focus_areas=["Authentication", "Authorization", "Data Protection"],
    heuristics=[
        "Check for SQL injection vulnerabilities",
        "Verify HTTPS usage",
        "Validate input sanitization"
    ],
    example_questions=[
        "Are there any auth bypass vectors?",
        "Is sensitive data encrypted at rest and in transit?"
    ],
    communication_style="Direct and actionable"
)
```

## Testing Patterns

### Unit Test
```python
import pytest
from unittest.mock import Mock, patch
from greybeard.analyzer import run_review
from greybeard.models import ReviewRequest, ContentPack

@pytest.fixture
def sample_pack():
    return ContentPack(
        name="test",
        perspective="Tester",
        tone="direct"
    )

@pytest.fixture
def sample_request(sample_pack):
    return ReviewRequest(
        mode="review",
        pack=sample_pack,
        input_text="code sample"
    )

def test_run_review_with_openai(sample_request):
    """Test run_review with OpenAI backend."""
    config = Mock()
    config.llm.backend = "openai"
    config.llm.resolved_model.return_value = "gpt-4"
    config.groq.available = False
    
    with patch("greybeard.analyzer._run_openai_compat") as mock_run:
        mock_run.return_value = ("review text", 100, 200)
        
        result = run_review(sample_request, config=config)
        
        assert "review text" in result
        mock_run.assert_called_once()

def test_run_review_groq_fallback_on_simple_task(sample_request):
    """Test Groq fallback for simple tasks."""
    config = Mock()
    config.llm.backend = "openai"
    config.llm.resolved_model.return_value = "gpt-4"
    config.groq.available = True
    config.groq.use_for_simple_tasks = True
    config.groq.model = "llama-3.1-8b"
    
    sample_request.input_text = "simple"
    
    with patch("greybeard.analyzer.is_simple_task", return_value=True):
        with patch("greybeard.analyzer.run_groq") as mock_groq:
            mock_groq.return_value = ("groq response", 50, 100)
            
            result = run_review(sample_request, config=config)
            
            assert "groq response" in result
            mock_groq.assert_called_once()
```

### Integration Test
```python
def test_analyze_cli_with_file(tmp_path):
    """Test CLI analyze command with file input."""
    import subprocess
    
    # Create test file
    test_file = tmp_path / "code.py"
    test_file.write_text("def hello():\n    print('hello')")
    
    # Run CLI
    result = subprocess.run(
        ["uv", "run", "greybeard", "analyze", str(test_file)],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0
    assert len(result.stdout) > 0  # Got some output
```

## Common Workflows

### Adding a New Backend
1. Create `greybeard/backends/my_backend.py`
2. Extend `Backend` base class
3. Implement `call()` and `call_async()` methods
4. Add to config `KNOWN_BACKENDS`
5. Write unit tests (mock API calls)
6. Document in README
7. PR with backend name and usage example

### Adding a Review Mode
1. Add entry to `REVIEW_MODES` dict in `greybeard/modes.py`
2. Define system prompt (clear, structured expectations)
3. Test with multiple LLM backends
4. Add example in docs
5. PR with usage example

### Creating a Content Pack
1. Create YAML file in `packs/`
2. Define perspective, tone, focus areas
3. Add heuristics and example questions
4. Test with `greybeard analyze --pack my-pack`
5. PR with documentation

### Fixing a Bug
1. Write failing test that reproduces bug
2. Fix the code
3. Verify test passes
4. Add edge case tests
5. PR with reproduction steps in description
