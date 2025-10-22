
import logging
from typing import Dict, Any
from mcp.server.fastmcp import FastMCP

# 1. Настраиваем базовую конфигурацию логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
log = logging.getLogger(__name__)

# 2. Создаем экземпляр приложения FastMCP.
log.info("Создание экземпляра FastMCP сервера...")
mcp_server = FastMCP()
log.info("Экземпляр FastMCP сервера создан.")

# 3. Определяем и регистрируем инструмент с помощью декоратора.
@mcp_server.tool()
async def get_weather(city: str) -> Dict[str, Any]:
    """
    Получает текущую погоду для заданного города.
    
    :param city: Город, для которого нужно получить погоду.
    """
    log.info(f"Инструмент 'get_weather' вызван с аргументом city='{city}'")
    
    # Имитация данных о погоде
    if city.lower() == "москва":
        result = {"temperature": "15°C", "condition": "Облачно"}
    elif city.lower() == "лондон":
        result = {"temperature": "12°C", "condition": "Дождь"}
    else:
        result = {"temperature": "20°C", "condition": "Солнечно"}
    
    log.info(f"Инструмент 'get_weather' возвращает результат: {result}")
    return result

log.info(f"Инструмент '{get_weather.__name__}' успешно зарегистрирован.")
log.info("MCP-сервер готов к запуску. Запустите его командой:")
log.info("uvicorn mcp_server.main:mcp_server --host 127.0.0.1 --port 8000")

