from app.core.config import settings
from app.main import app


def test_catalog_routes_are_registered_without_public_auth_requirement() -> None:
    schema = app.openapi()
    catalog_path = f"{settings.API_V1_STR}/catalog"
    detail_path = f"{catalog_path}/{{slug}}"
    admin_path = f"{settings.API_V1_STR}/admin/catalog/{{slug}}"

    assert catalog_path in schema["paths"]
    assert detail_path in schema["paths"]
    assert admin_path in schema["paths"]

    assert "security" not in schema["paths"][catalog_path]["get"]
    assert "security" not in schema["paths"][detail_path]["get"]
    assert schema["paths"][admin_path]["post"]["security"]
    assert schema["paths"][admin_path]["patch"]["security"]
    assert schema["paths"][admin_path]["delete"]["security"]


def test_catalog_openapi_exposes_documentation_shapes_without_auth_requirement() -> None:
    schema = app.openapi()
    schemas = schema["components"]["schemas"]

    assert "CatalogPage" in schemas
    assert "ApiDetail" in schemas
    assert schemas["ApiDetail"]["properties"]["auth"]["$ref"].endswith(
        "/ApiAuth"
    )


def test_api_key_auth_boundary_is_explicit_in_openapi() -> None:
    schema = app.openapi()
    security_schemes = schema["components"]["securitySchemes"]
    api_key_schemes = {
        name: value
        for name, value in security_schemes.items()
        if value.get("type") == "apiKey" and value.get("in") == "header"
    }

    assert api_key_schemes
    assert any(
        scheme.get("name") == "X-API-Key" for scheme in api_key_schemes.values()
    )
    protected_paths = [
        path_item
        for path, path_item in schema["paths"].items()
        if "api-keys/public-auth-check" in path
    ]
    assert protected_paths
    assert any(
        operation.get("security")
        for path_item in protected_paths
        for operation in path_item.values()
        if isinstance(operation, dict)
    )


def test_api_key_protected_route_declares_structured_errors() -> None:
    schema = app.openapi()
    operation = schema["paths"][
        f"{settings.API_V1_STR}/api-keys/public-auth-check"
    ]["get"]

    assert operation["responses"]["401"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/ApiErrorResponse")
    assert operation["responses"]["403"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/ApiErrorResponse")
