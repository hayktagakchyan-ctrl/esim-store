"""
Клиент для API esimaccess.com — партнёрский (реселлерский) API.
Источник: официальная документация (docs.esimaccess.com), актуально на момент написания.

Подтверждено документацией (можно использовать как есть):
- base_url = https://api.esimaccess.com
- Авторизация — ОДИН заголовок "RT-AccessCode: <твой код>", без HMAC-подписи.
  Ключ выдаётся в личном кабинете esimaccess.
- Все запросы — POST с JSON-телом (даже там, где тело фактически пустое: body="").
- Обёртка ответа: {"success": bool, "errorCode": str, "errorMsg": str|null, "obj": {...}}
- Rate limit: 8 запросов в секунду — ниже есть примитивный ограничитель на это.
- balance/query, location/list, esim/usage/query — пути и формат ответа подтверждены документацией.
- esim/order ("Order Profiles", создание заказа) — подтверждено, см. create_order() ниже.
- esim/query ("Query All Allocated Profiles") — полностью подтверждено, включая то, что
  `pager` обязателен даже при запросе по orderNo, и что ответ — список esimList
  (может быть несколько eSIM на один orderNo, у нас всегда один, см. query_esim()).

ЕЩЁ НЕ ПОДТВЕРЖДЕНО (нужна ещё одна страница документации, прежде чем полностью
избавиться от заглушек):
- Список пакетов с ценами ("Query All Data Packages") — путь эндпоинта не приведён,
  только упомянут в истории версий. Пришли эту страницу — и list_packages() перестанет
  быть заглушкой, а create_order() сможет дополнительно сверять цену (см. его docstring).
"""
from __future__ import annotations

import time
import asyncio
from collections import deque

import httpx

from app.config import settings


class ESimAccessError(Exception):
    """Бизнес-ошибка от esimaccess (success=false) — errorCode/errorMsg из их ответа."""

    def __init__(self, error_code: str, error_msg: str | None):
        self.error_code = error_code
        self.error_msg = error_msg
        super().__init__(f"[{error_code}] {error_msg}")


class _RateLimiter:
    """Простой ограничитель — не больше N вызовов в секунду (лимит esimaccess: 8/сек)."""

    def __init__(self, max_per_second: int = 8):
        self._max = max_per_second
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            while self._timestamps and now - self._timestamps[0] > 1.0:
                self._timestamps.popleft()
            if len(self._timestamps) >= self._max:
                sleep_for = 1.0 - (now - self._timestamps[0])
                if sleep_for > 0:
                    await asyncio.sleep(sleep_for)
            self._timestamps.append(time.monotonic())


class ESimAccessClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url="https://api.esimaccess.com",
            headers={
                "RT-AccessCode": settings.ESIMACCESS_ACCESS_CODE,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        self._rate_limiter = _RateLimiter(max_per_second=8)

    async def close(self) -> None:
        await self._client.aclose()

    async def _post(self, path: str, json: dict | None = None) -> dict:
        await self._rate_limiter.acquire()
        response = await self._client.post(path, json=json or {})
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ESimAccessError(str(exc.response.status_code), exc.response.text)
        except httpx.RequestError as exc:
            raise ESimAccessError("network_error", str(exc))

        data = response.json()
        if not data.get("success", False):
            raise ESimAccessError(data.get("errorCode", "unknown"), data.get("errorMsg"))
        return data.get("obj", {})

    # --- Подтверждено документацией ---

    async def get_balance(self) -> dict:
        """POST /api/v1/open/balance/query — баланс аккаунта у esimaccess."""
        return await self._post("/api/v1/open/balance/query")

    async def list_locations(self) -> list[dict]:
        """
        POST /api/v1/open/location/list — список поддерживаемых стран/регионов
        (code, name, type: 1=страна, 2=мульти-региональный пакет с subLocationList).
        Полезно для построения списка стран в каталоге уже сейчас, до появления
        эндпоинта цен на пакеты.
        """
        result = await self._post("/api/v1/open/location/list")
        return result.get("locationList", [])

    async def get_esim_usage(self, esim_tran_no_list: list[str]) -> list[dict]:
        """
        POST /api/v1/open/esim/usage/query — остаток трафика по esimTranNo (не по iccid!).
        До 10 esimTranNo за один вызов. Данные обновляются раз в 2-3 часа, не realtime.
        """
        result = await self._post(
            "/api/v1/open/esim/usage/query", {"esimTranNoList": esim_tran_no_list[:10]}
        )
        return result.get("esimUsageList", [])

    async def query_esim(
        self, *, order_no: str | None = None, iccid: str | None = None, page_size: int = 50
    ) -> list[dict]:
        """
        POST /api/v1/open/esim/query — "Query All Allocated Profiles". Полностью
        подтверждено документацией. `pager` у них MANDATORY даже при запросе по
        orderNo — раньше это было упущено, теперь передаём всегда.

        По orderNo может вернуться несколько eSIM (батч-заказ) — у нас count всегда 1,
        так что вызывающий код просто берёт esimList[0]. Если esimList пуст и/или
        errorCode == "200010" — профили ещё не готовы (SM-DP+ их выделяет, до ~30 сек),
        это нормально, не финальная ошибка — вызывающий код (вебхук ORDER_STATUS)
        уже это учитывает, оставляя заказ в PROVISIONING на случай повторной попытки.

        Для проверки статуса уже выданного eSIM позже (не сразу после заказа) лучше
        передавать esimTranNo, а не iccid — iccid переиспользуются (см. документацию),
        а вот для самой первой выдачи сразу после заказа он ещё не известен, поэтому
        здесь ищем по orderNo.
        """
        payload: dict = {"pager": {"pageNum": 1, "pageSize": page_size}}
        if order_no:
            payload["orderNo"] = order_no
        if iccid:
            payload["iccid"] = iccid

        result = await self._post("/api/v1/open/esim/query", payload)
        return result.get("esimList", [])

    async def create_order(
        self,
        *,
        transaction_id: str,
        package_code: str,
        count: int = 1,
        price: int | None = None,
        period_num: int | None = None,
    ) -> str:
        """
        POST /api/v1/open/esim/order — "Order Profiles". Подтверждено документацией.

        - transaction_id: наш собственный уникальный ID (Order.our_transaction_id) —
          esimaccess дедуплицирует повторные вызовы по нему, так что при сетевых
          ошибках/ретраях безопасно вызывать с тем же transaction_id повторно.
        - package_code: slug пакета (они явно рекомендуют slug, а не старый packageCode).
        - price: НАМЕРЕННО не передаём по умолчанию (см. ниже).

        Возвращает orderNo. Дальше по нему — esimaccess_client.query_esim(order_no)
        (см. выше) или дождаться вебхука ORDER_STATUS/GOT_RESOURCE.

        Про price/amount: в API это необязательная "сверка цены" — но передавать её
        осмысленно можно, только когда у нас в базе реально совпадает актуальная цена
        esimaccess (список пакетов/цен, "Query All Data Packages", пока не подтверждён
        документацией — см. list_packages ниже). Несовпадение цены — это отдельная
        ошибка (200005/200006), а не просто предупреждение. Поэтому пока безопаснее
        не передавать price/amount вовсе (эти поля optional) и просто доверять
        текущей цене esimaccess — как только появится подтверждённый список пакетов
        с ценами, стоит начать передавать price для дополнительной защиты от рассинхрона.
        """
        package_info: dict = {"packageCode": package_code, "count": count}
        if price is not None:
            package_info["price"] = price
        if period_num is not None:
            package_info["periodNum"] = period_num

        payload: dict = {"transactionId": transaction_id, "packageInfoList": [package_info]}
        if price is not None:
            payload["amount"] = price * count

        result = await self._post("/api/v1/open/esim/order", payload)
        return result["orderNo"]

    # --- НЕ ПОДТВЕРЖДЕНО ДОКУМЕНТАЦИЕЙ — см. docstring ниже ---

    async def list_packages(self, location_code: str | None = None) -> list[dict]:
        """
        Путь эндпоинта и формат ответа НЕ подтверждены документацией esimaccess —
        угадано по аналогии с остальными эндпоинтами (все следуют схеме
        "ресурс/действие": esim/order, esim/query, balance/query, location/list).

        Перед тем как полагаться на это по-настоящему — проверь кнопкой
        «🧪 Тест импорта» в админке (/products... то есть /packages/import) на
        одной стране. Если придёт ошибка или пустой список — значит путь/формат
        ответа отличается от угаданного, тогда нужно либо получить страницу
        "Query All Data Packages" из документации esimaccess, либо разобрать
        реальный ответ по логам ошибки.

        Поля пакета в ответе — тоже по аналогии с тем, что уже подтверждено в
        других местах их API: rawPrice (целое, /10000 = доллары — та же схема,
        что и в create_order), slug/packageCode, volume (байты), duration.
        """
        payload: dict = {"pager": {"pageNum": 1, "pageSize": 200}}
        if location_code:
            payload["locationCode"] = location_code

        result = await self._post("/api/v1/open/package/list", payload)

        raw_list = (
            result.get("packageList")
            or result.get("list")
            or result.get("packages")
            or (result if isinstance(result, list) else [])
        )

        packages = []
        for item in raw_list:
            raw_price = item.get("rawPrice")
            cost_price = (raw_price / 10000) if raw_price is not None else None
            volume_bytes = item.get("volume") or item.get("totalVolume")
            data_amount_mb = round(volume_bytes / (1024 * 1024)) if volume_bytes else None
            packages.append({
                "package_code": item.get("slug") or item.get("packageCode"),
                "title": item.get("name") or item.get("title") or "",
                "cost_price": cost_price,
                "data_amount_mb": data_amount_mb,
                "validity_days": item.get("duration") or item.get("totalDuration"),
                "country_code": item.get("locationCode") or location_code,
                "raw": item,
            })
        return packages


esimaccess_client = ESimAccessClient()
