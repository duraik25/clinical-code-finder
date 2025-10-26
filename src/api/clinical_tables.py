import aiohttp
import asyncio
from typing import List, Dict, Any, Optional
import logging
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class ClinicalTablesAPI:
    """Async wrapper for NIH Clinical Tables API"""

    BASE_URL = "https://clinicaltables.nlm.nih.gov/api"

    # API-specific configurations
    API_CONFIG = {
        "icd10cm": {
            "search_fields": "code,name",
            "display_fields": "code,name",
            "result_index": 3,
            "code_field": 0,
            "display_field": 1
        },
        "loinc_items": {
            "search_fields": "text,COMPONENT,CONSUMER_NAME,RELATEDNAMES2,METHOD_TYP,SHORTNAME,LONG_COMMON_NAME,LOINC_NUM",
            "display_fields": "LOINC_NUM,LONG_COMMON_NAME",
            "result_index": 3,
            "code_field": 0,
            "display_field": 1
        },
        "rxterms": {
            "search_fields": "DISPLAY_NAME,STRENGTHS_AND_FORMS,DISPLAY_NAME_SYNONYM",
            "display_fields": "RXCUIS,DISPLAY_NAME",
            "result_index": 3,
            "code_field": 0,
            "display_field": 1
        },
        "hcpcs": {
            "search_fields": "code,short_desc,long_desc",
            "display_fields": "code,display",
            "result_index": 3,
            "code_field": 0,
            "display_field": 1
        },
        "ucum": {
            "search_fields": "cs_code,name,synonyms,cs_code_tokens",
            "display_fields": "cs_code,name",
            "result_index": 3,
            "code_field": 0,
            "display_field": 1
        },
        "hpo": {
            "search_fields": "id,name,synonym.term",
            "display_fields": "id,name",
            "result_index": 3,
            "code_field": 0,
            "display_field": 1
        }
    }

    def __init__(self, timeout: int = 30):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        connector = aiohttp.TCPConnector(ssl=False)
        self.session = aiohttp.ClientSession(
            timeout=self.timeout,
            connector=connector
        )
        logger.warning("SSL verification disabled for development")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def search(
            self,
            endpoint: str,
            query: str,
            limit: int = 10
    ) -> List[Dict[str, Any]]:
        if not self.session:
            connector = aiohttp.TCPConnector(ssl=False)
            self.session = aiohttp.ClientSession(timeout=self.timeout, connector=connector)

        # Get API-specific configuration
        config = self.API_CONFIG.get(endpoint, self.API_CONFIG["icd10cm"])

        params = {
            "sf": config["search_fields"],
            "df": config["display_fields"],
            "maxList": limit,
            "terms": query
        }

        url = f"{self.BASE_URL}/{endpoint}/v3/search?{urlencode(params)}"

        logger.info(f"Searching {endpoint} for: {query}")
        logger.info(f"URL: {url}")

        try:
            async with self.session.get(url) as response:
                response.raise_for_status()
                data = await response.json()

                # Parse based on API response structure
                result_index = config["result_index"]
                if len(data) > result_index and isinstance(data[result_index], list):
                    results = []
                    for item in data[result_index]:
                        if isinstance(item, list) and len(item) >= 2:
                            code = item[config["code_field"]]
                            display = item[config["display_field"]]

                            # Clean up display text
                            if not display or display.strip() == "":
                                display = f"{endpoint.upper()}: {code}"

                            results.append({
                                "code": code,
                                "display": display,
                                "system": endpoint  # Clean system name
                            })
                    logger.info(f"Results: {results}")
                    logger.info(f"Found {len(results)} results from {endpoint}")
                    return results
                else:
                    logger.warning(f"Unexpected response structure from {endpoint}: {data}")
                    return []

        except Exception as e:
            logger.error(f"API call failed for {endpoint}: {e}")
            return []
