"""Calculator tool for evaluating mathematical expressions."""

import ast
import operator
from typing import Any

from agent_orchestrator.tools.base import BaseTool, ToolResult


class CalculatorTool(BaseTool):
    """Tool for safely evaluating mathematical expressions.

    Supports basic arithmetic operations: +, -, *, /, **, %, //
    Also supports parentheses for grouping.
    """

    name = "calculator"
    description = (
        "Evaluate a mathematical expression. Supports basic arithmetic "
        "(+, -, *, /, **, %, //) and parentheses. Example: '(2 + 3) * 4'"
    )

    # Allowed operators for safe evaluation
    _operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def get_input_schema(self) -> dict:
        """Get the JSON Schema for calculator input."""
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate",
                }
            },
            "required": ["expression"],
        }

    async def execute(self, expression: str, **kwargs: Any) -> ToolResult:
        """Evaluate a mathematical expression safely.

        Args:
            expression: Mathematical expression to evaluate.

        Returns:
            ToolResult with the calculated value or error.
        """
        try:
            result = self._safe_eval(expression)
            return ToolResult(success=True, output=result)
        except (ValueError, TypeError, SyntaxError, ZeroDivisionError) as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _safe_eval(self, expression: str) -> float | int:
        """Safely evaluate a mathematical expression.

        Args:
            expression: Expression to evaluate.

        Returns:
            Calculated result.

        Raises:
            ValueError: If expression contains invalid operations.
        """
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as e:
            raise ValueError(f"Invalid expression syntax: {e}")

        return self._eval_node(tree.body)

    def _eval_node(self, node: ast.AST) -> float | int:
        """Recursively evaluate an AST node.

        Args:
            node: AST node to evaluate.

        Returns:
            Evaluated value.

        Raises:
            ValueError: If node type is not allowed.
        """
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Invalid constant type: {type(node.value)}")

        elif isinstance(node, ast.BinOp):
            op_func = self._operators.get(type(node.op))
            if op_func is None:
                raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            return op_func(left, right)

        elif isinstance(node, ast.UnaryOp):
            op_func = self._operators.get(type(node.op))
            if op_func is None:
                raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
            operand = self._eval_node(node.operand)
            return op_func(operand)

        elif isinstance(node, ast.Expression):
            return self._eval_node(node.body)

        else:
            raise ValueError(f"Unsupported expression type: {type(node).__name__}")
