"""
Расширенный HTTP MCP сервер
Сохраните как: advanced_http_server.py
"""

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.session import ServerSession
import asyncio

# Создаём сервер
mcp = FastMCP(
    name="AdvancedHTTPServer",
    instructions="Расширенный HTTP сервер с прогрессом и логированием"
)

@mcp.tool()
async def long_calculation(
    n: int,
    ctx: Context[ServerSession, None]
) -> str:
    """Длительное вычисление с прогрессом"""
    await ctx.info(f"Начинаю вычисление для n={n}")

    total_steps = 10
    result = 0

    for i in range(total_steps):
        # Симулируем работу
        await asyncio.sleep(0.5)
        result += i * n

        # Отправляем прогресс
        progress = (i + 1) / total_steps
        await ctx.report_progress(
            progress=progress,
            total=1.0,
            message=f"Шаг {i + 1}/{total_steps}"
        )
        await ctx.debug(f"Промежуточный результат: {result}")

    await ctx.info("Вычисление завершено!")
    return f"Итоговый результат: {result}"

@mcp.tool()
def factorial(n: int) -> int:
    """Вычисляет факториал числа"""
    if n < 0:
        raise ValueError("Факториал определён только для неотрицательных чисел")
    if n == 0 or n == 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result

@mcp.tool()
def fibonacci(n: int) -> list[int]:
    """Возвращает последовательность Фибоначчи длиной n"""
    if n <= 0:
        return []
    if n == 1:
        return [0]

    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i-1] + fib[i-2])
    return fib

@mcp.resource("data://stats")
def get_stats() -> str:
    """Статистика сервера"""
    import datetime
    return f"""
    Статистика сервера
    ==================
    Время запуска: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    Доступных инструментов: 4
    Статус: Активен ✅
    """

if __name__ == "__main__":
    import sys

    # Можно указать порт из аргументов командной строки
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000

    print(f"🚀 Запуск HTTP MCP сервера на порту {port}...")
    print(f"📍 URL: http://localhost:{port}/mcp")
    print("📝 Нажмите Ctrl+C для остановки")

    # Настройка порта
    mcp.settings.port = port

    # Запуск
    mcp.run(transport="streamable-http")
