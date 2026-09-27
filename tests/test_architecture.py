from pathlib import Path
import ast
import unittest


ROOT = Path(__file__).parents[1] / "src" / "hotel_management"


class ArchitectureTests(unittest.TestCase):
    def imports_for(self, layer: str) -> list[str]:
        imports = []
        for path in (ROOT / layer).rglob("*.py"):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
        return imports

    def test_domain_is_framework_free_and_infrastructure_free(self):
        imports = self.imports_for("domain")
        forbidden_prefixes = (
            "infrastructure",
            "http",
            "sqlalchemy",
            "django",
            "fastapi",
            "flask",
        )
        self.assertFalse(
            any(item.startswith(prefix) for item in imports for prefix in forbidden_prefixes)
        )

    def test_application_depends_only_on_domain_and_standard_library(self):
        imports = self.imports_for("application")
        self.assertFalse(any(item.startswith("hotel_management.infrastructure") for item in imports))
        self.assertFalse(any(item.startswith("hotel_management.interfaces") for item in imports))

    def test_use_cases_do_not_construct_infrastructure(self):
        for path in (ROOT / "application").rglob("*.py"):
            source = path.read_text()
            self.assertNotIn("InMemory", source)
            self.assertNotIn("Postgres", source)
            self.assertNotIn("new ", source)


if __name__ == "__main__":
    unittest.main()
