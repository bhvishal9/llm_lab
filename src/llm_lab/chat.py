import os
import sys

from google.genai.errors import ClientError
from dataclasses import dataclass
from google import genai


@dataclass
class Config:
    api_key: str
    model_name: str


def get_required_env(name: str) -> str:
    """Read, strip, and validate a required env var."""
    raw = os.getenv(name)
    if raw is None:
        raise ValueError(f"Environment variable {name} not found")
    value = raw.strip()
    if not value:
        raise ValueError(f"Environment variable {name} is empty")
    return value


def get_optional_env(name: str, default: str) -> str:
    """Read, strip, and fall back to default if empty/whitespace."""
    raw = os.getenv(name, default)
    value = raw.strip()
    if not value:
        return default
    return value


def load_config() -> Config:
    api_key = get_required_env("LLM_API_KEY")
    model_name = get_optional_env("LLM_MODEL_NAME", "gemini-2.5-flash")
    return Config(api_key=api_key, model_name=model_name)


def print_exit() -> None:
    print("\nGoodbye!")


def chat_loop(client: genai.Client, config: Config) -> None:
    print("Welcome to the chat! Type '/exit' to quit.\n")
    while True:
        try:
            user_input = input("[You]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print_exit()
            return
        if user_input.lower() == "/exit":
            print_exit()
            return
        if not user_input:
            continue
        response = client.models.generate_content(
            model=config.model_name, contents=user_input
        )
        print(f"[Gemini]: {response.text}")


def main() -> int:
    try:
        config = load_config()
        client = genai.Client(api_key=config.api_key)
        chat_loop(client, config)
    except ValueError as err:
        print(f"Config Error: {err}")
        return 1
    except ClientError as err:
        print(f"LLM Client Error: {err}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
