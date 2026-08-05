"""
Herramienta: Calculator — Sesión 7
=====================================
Herramienta de cálculo matemático seguro para el agente LLM.

Por qué necesitamos esto:
  Los LLMs son malos para matemáticas exactas. "1234 * 5678" puede
  dar respuestas incorrectas directamente desde el modelo.
  Con esta herramienta, la calculadora (Python) hace el cálculo
  exacto y el LLM solo interpreta y presenta el resultado.

Seguridad:
  Usamos ast.literal_eval + evaluación segura para evitar
  que el agente ejecute código arbitrario como:
  - os.system("rm -rf /")
  - import subprocess; ...
"""

import ast
import math
import logging
import operator
from typing import Any

logger = logging.getLogger(__name__)


class CalculatorTool:
    """
    Calculadora matemática segura para el agente LLM.

    Operaciones soportadas:
    - Aritméticas: +, -, *, /, //, %, **
    - Funciones: sqrt, sin, cos, tan, log, abs, round, ceil, floor
    - Constantes: pi, e

    Uso por el agente:
        Action: calculator
        Action Input: 1234 * 5678
        Observation: 7006652

        Action: calculator
        Action Input: sqrt(144)
        Observation: 12.0
    """

    name = "calculator"
    description = (
        "Realiza cálculos matemáticos. "
        "Input: expresión matemática (ej: '1234 * 5678', 'sqrt(144)', '(100 + 50) * 0.21'). "
        "Soporta +, -, *, /, **, sqrt, sin, cos, log, round, abs."
    )

    # Funciones y constantes permitidas (whitelist de seguridad)
    _SAFE_NAMES: dict[str, Any] = {
        # Constantes matemáticas
        "pi": math.pi,
        "e": math.e,
        "inf": math.inf,
        # Funciones de math
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log,
        "log2": math.log2,
        "log10": math.log10,
        "exp": math.exp,
        "abs": abs,
        "round": round,
        "ceil": math.ceil,
        "floor": math.floor,
        "pow": math.pow,
        "factorial": math.factorial,
        # Built-ins seguros
        "min": min,
        "max": max,
        "sum": sum,
    }

    async def run(self, expression: str) -> str:
        """
        Evaluar expresión matemática de forma segura.

        Args:
            expression: Expresión matemática como string

        Returns:
            Resultado como string
        """
        try:
            # Limpiar input
            expr = expression.strip().replace(",", "").replace("×", "*").replace("÷", "/")

            # Parsear el AST de la expresión
            tree = ast.parse(expr, mode="eval")

            # Verificar que solo contiene operaciones seguras
            self._validate_ast(tree)

            # Evaluar con contexto seguro
            result = eval(  # noqa: S307
                compile(tree, "<string>", "eval"),
                {"__builtins__": {}},
                self._SAFE_NAMES,
            )

            # Formatear el resultado
            if isinstance(result, float):
                if result == int(result) and abs(result) < 1e15:
                    formatted = f"{int(result):,}"
                else:
                    formatted = f"{result:.6g}"
            elif isinstance(result, int):
                formatted = f"{result:,}"
            else:
                formatted = str(result)

            logger.info(f"🔢 Calculator: {expr} = {formatted}")
            return formatted

        except ZeroDivisionError:
            return "Error: División por cero"
        except ValueError as e:
            return f"Error matemático: {e}"
        except PermissionError:
            return "Error: Operación no permitida por seguridad"
        except Exception as e:
            logger.warning(f"Calculator error para '{expression}': {e}")
            return f"No pude calcular '{expression}'. Usa formato como: 100 * 200, sqrt(144)"

    def _validate_ast(self, tree: ast.Expression):
        """
        Validar que el AST solo contiene operaciones seguras.
        Lanza PermissionError si encuentra algo peligroso.
        """
        allowed_nodes = (
            ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num,
            ast.Constant, ast.Name, ast.Call, ast.Load,
            # Operadores permitidos
            ast.Add, ast.Sub, ast.Mult, ast.Div,
            ast.FloorDiv, ast.Mod, ast.Pow,
            ast.USub, ast.UAdd,
            # Para funciones con múltiples args
            ast.keyword,
        )
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id not in self._SAFE_NAMES:
                raise PermissionError(f"Nombre no permitido: {node.id}")
            if not isinstance(node, allowed_nodes):
                raise PermissionError(f"Operación no permitida: {type(node).__name__}")
