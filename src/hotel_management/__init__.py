"""Hotel management system.

The package is intentionally layered:

* ``domain`` contains business rules and no framework code.
* ``application`` orchestrates use cases through ports.
* ``infrastructure`` implements ports.
* ``interfaces`` adapts HTTP input/output.
* ``composition`` wires the application together.
"""
