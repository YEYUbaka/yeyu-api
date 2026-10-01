from pathlib import Path

COMPOSE_FILE = Path(__file__).resolve().parents[2] / "compose.yml"


def _backend_environment_mapping() -> dict[str, str]:
    lines = COMPOSE_FILE.read_text(encoding="utf-8").splitlines()
    backend_index = lines.index("  backend:")
    environment_index = lines.index("    environment:", backend_index)

    environment_lines: list[str] = []
    for line in lines[environment_index + 1 :]:
        if line and not line.startswith("      "):
            break
        if line.strip():
            environment_lines.append(line.strip())

    return {
        key: value.strip()
        for key, value in (line.split(":", maxsplit=1) for line in environment_lines)
    }


def test_compose_passes_versioned_api_key_peppers_without_storing_values() -> None:
    environment = _backend_environment_mapping()

    expected_interpolations = {
        "API_KEY_PEPPER": "${API_KEY_PEPPER:-}",
        "API_KEY_PEPPER_VERSION": "${API_KEY_PEPPER_VERSION:-1}",
        "API_KEY_PREVIOUS_PEPPER": "${API_KEY_PREVIOUS_PEPPER:-}",
        "API_KEY_PREVIOUS_PEPPER_VERSION": "${API_KEY_PREVIOUS_PEPPER_VERSION:-}",
    }

    assert {
        key: environment.get(key) for key in expected_interpolations
    } == expected_interpolations
