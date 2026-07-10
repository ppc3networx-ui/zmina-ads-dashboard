"""
gads.py - общий read-only клиент Google Ads API для всех продуктов.

Ничего не пишет в аккаунт, только запросы на чтение (GAQL search_stream).

Аутентификация: Application Default Credentials (ADC) + developer token.
Работает в двух режимах одним и тем же кодом:

  - Локально: gcloud auth application-default login \
        --scopes=https://www.googleapis.com/auth/adwords
    (создаёт ~/.config/gcloud/application_default_credentials.json,
    google.auth.default() подхватывает его сам)

  - В CI/cron (например GitHub Actions): переменная окружения
    GOOGLE_APPLICATION_CREDENTIALS указывает на JSON-ключ сервисного
    аккаунта. Email этого сервисного аккаунта нужно один раз пригласить
    как пользователя в Google Ads (Админ -> Доступ и безопасность),
    как обычно "шарят" Google-таблицу с сервисным аккаунтом.

В обоих случаях также нужно:
  export GOOGLE_ADS_DEVELOPER_TOKEN="ваш_developer_token"
  export GOOGLE_ADS_LOGIN_CUSTOMER_ID="id_менеджер_аккаунта"   # опционально, если customer_id под MCC

sync.py импортирует отсюда get_client() и run_search() и переиспользует
этот модуль для всех продуктов - здесь не должно быть логики,
специфичной для конкретного продукта.
"""
import os

import google.auth
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

API_VERSION = "v18"  # при необходимости обновить на актуальную версию API
ADWORDS_SCOPE = "https://www.googleapis.com/auth/adwords"


def get_client() -> GoogleAdsClient:
    """Собирает GoogleAdsClient на ADC (google.auth.default) + developer token."""
    developer_token = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN")
    if not developer_token:
        raise RuntimeError(
            "Не задан GOOGLE_ADS_DEVELOPER_TOKEN. "
            "Выполните: export GOOGLE_ADS_DEVELOPER_TOKEN=... перед запуском."
        )

    try:
        credentials, _ = google.auth.default(scopes=[ADWORDS_SCOPE])
    except google.auth.exceptions.DefaultCredentialsError as ex:
        raise RuntimeError(
            "Не найдены ADC. Локально выполните "
            "'gcloud auth application-default login --scopes=" + ADWORDS_SCOPE + "', "
            "в CI задайте GOOGLE_APPLICATION_CREDENTIALS с JSON-ключом сервисного аккаунта."
        ) from ex

    login_customer_id = os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID")

    return GoogleAdsClient(
        credentials=credentials,
        developer_token=developer_token,
        login_customer_id=login_customer_id.replace("-", "") if login_customer_id else None,
        version=API_VERSION,
    )


def run_search(client: GoogleAdsClient, customer_id: str, query: str):
    """Выполняет GAQL-запрос через search_stream и возвращает список строк."""
    ga_service = client.get_service("GoogleAdsService")
    customer_id = customer_id.replace("-", "")
    try:
        stream = ga_service.search_stream(customer_id=customer_id, query=query)
        rows = []
        for batch in stream:
            rows.extend(batch.results)
        return rows
    except GoogleAdsException as ex:
        details = "; ".join(e.message for e in ex.failure.errors)
        raise RuntimeError(
            f"Ошибка Google Ads API (customer_id={customer_id}): {details}"
        ) from ex
