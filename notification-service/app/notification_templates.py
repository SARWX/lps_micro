"""
Модуль для работы с шаблонами уведомлений.
Содержит логику обработки шаблонов и их рендеринга.
"""
import logging
from typing import Dict, Any, Optional, List
from jinja2 import Template, Environment, meta
from app.database import get_template_by_id

logger = logging.getLogger(__name__)

_env = Environment()

async def render_template(template_id: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Рендеринг шаблона с контекстом.
    
    Args:
        template_id: ID шаблона
        context: Контекстные данные
        
    Returns:
        Optional[Dict[str, Any]]: Отрендеренный шаблон или None если шаблон не найден
    """
    try:
        template_data = get_template_by_id(template_id)
        if not template_:
            logger.warning(f"Template {template_id} not found")
            return None
        
        content = template_data.get('content', {})
        subject = content.get('subject', '')
        body = content.get('body', '')
        html_body = content.get('html_body', '')
        
        # Рендерим subject
        if subject:
            subject_template = Template(subject)
            subject = subject_template.render(**context)
        
        # Рендерим body
        if body:
            body_template = Template(body)
            body = body_template.render(**context)
        
        # Рендерим html_body
        if html_body:
            html_body_template = Template(html_body)
            html_body = html_body_template.render(**context)
        
        return {
            'subject': subject,
            'body': body,
            'html_body': html_body
        }
    
    except Exception as e:
        logger.error(f"Error rendering template {template_id}: {e}")
        return None

async def extract_template_variables(template_content: str) -> List[str]:
    """
    Извлечение переменных из шаблона.
    
    Args:
        template_content: Содержимое шаблона
        
    Returns:
        List[str]: Список переменных
    """
    try:
        parsed_content = _env.parse(template_content)
        variables = meta.find_undeclared_variables(parsed_content)
        return list(variables)
    except Exception as e:
        logger.error(f"Error extracting template variables: {e}")
        return []

async def validate_template(template_content: str, context: Dict[str, Any]) -> bool:
    """
    Валидация шаблона с контекстом.
    
    Args:
        template_content: Содержимое шаблона
        context: Контекстные данные
        
    Returns:
        bool: True если шаблон валиден
    """
    try:
        template = Template(template_content)
        template.render(**context)
        return True
    except Exception as e:
        logger.error(f"Template validation failed: {e}")
        return False