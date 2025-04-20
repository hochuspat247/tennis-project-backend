from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from sqlalchemy.sql import text  # Импортируем text для текстовых SQL-запросов
from app.db.session import get_db
from app.dependencies import get_current_active_user
from app.db.models import User as UserModel
from typing import List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tables", tags=["tables"])

@router.get("/", response_model=List[str], summary="Получить список таблиц базы данных")
async def get_tables(db: Session = Depends(get_db), current_user: Optional[UserModel] = Depends(get_current_active_user)):
    """
    Возвращает список всех таблиц в базе данных.

    **Доступ**: Доступно всем пользователям, включая неаутентифицированных.

    **Примечание**: Если пользователь аутентифицирован, его действия логируются.

    **Пример ответа**:
    ```json
    ["users", "bookings", "courts"]
    ```

    **Ошибки**:
    - 500: Ошибка сервера при получении списка таблиц.
    """
    try:
        inspector = inspect(db.bind)
        tables = inspector.get_table_names()
        if current_user:
            logger.info(f"User {current_user.id} retrieved list of tables: {tables}")
        else:
            logger.info(f"Anonymous user retrieved list of tables: {tables}")
        return tables
    except Exception as e:
        logger.error(f"Error retrieving tables: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve tables")

@router.delete("/{table_name}/clear", status_code=status.HTTP_204_NO_CONTENT, summary="Очистить данные в указанной таблице")
async def clear_table(table_name: str, db: Session = Depends(get_db), current_user: Optional[UserModel] = Depends(get_current_active_user)):
    """
    Очищает все данные в указанной таблице (не удаляет структуру таблицы).

    **Параметры**:
    - **table_name**: Имя таблицы (например, `users`, `bookings`).

    **Доступ**: Доступно всем пользователям, включая неаутентифицированных.

    **Предупреждение**: Действие необратимо, все данные в таблице будут удалены. Используйте с осторожностью.

    **Ошибки**:
    - 400: Таблица не существует или имя некорректно.
    - 500: Ошибка сервера при очистке таблицы.

    **Пример запроса**:
    ```
    DELETE /api/tables/users/clear
    ```
    """
    try:
        inspector = inspect(db.bind)
        tables = inspector.get_table_names()
        if table_name not in tables:
            logger.warning(f"Attempted to clear non-existent table: {table_name}")
            raise HTTPException(status_code=400, detail=f"Table '{table_name}' does not exist")

        # Используем text() для безопасного выполнения SQL-запроса
        db.execute(text(f"DELETE FROM {table_name}"))
        db.commit()
        if current_user:
            logger.info(f"User {current_user.id} cleared table: {table_name}")
        else:
            logger.info(f"Anonymous user cleared table: {table_name}")
        return None
    except Exception as e:
        db.rollback()
        logger.error(f"Error clearing table {table_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clear table '{table_name}'")