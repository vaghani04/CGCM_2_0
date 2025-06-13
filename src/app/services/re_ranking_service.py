import httpx
from fastapi import HTTPException

from src.app.config.settings import settings
from src.app.utils.logging_util import loggers


class RerankerService:
    def __init__(self):
        self.voyage_api_key = settings.VOYAGEAI_API_KEY
        self.voyage_base_url = settings.VOYAGEAI_BASE_URL
        self.RERANK_SUFFIX = "rerank"
        self.timeout = httpx.Timeout(
            connect=60.0,  # Time to establish a connection
            read=120.0,  # Time to read the response
            write=120.0,  # Time to send data
            pool=60.0,  # Time to wait for a connection from the pool
        )

    async def voyage_rerank(
        self, model_name: str, query: str, documents: list, top_n: int
    ):
        headers = {
            "content-type": "application/json",
            "Authorization": f"Bearer {self.voyage_api_key}",
        }

        payload = {
            "model": model_name,
            "query": query,
            "top_k": top_n,
            "documents": documents,
        }

        rerank_url = f"{self.voyage_base_url}/{self.RERANK_SUFFIX}"

        try:
            async with httpx.AsyncClient(
                verify=False, timeout=self.timeout
            ) as client:
                response = await client.post(
                    rerank_url, headers=headers, json=payload
                )
                response.raise_for_status()
                loggers["voyageai"].info(
                    f"Reranking model hosted by Voyage tokens usage : {response.json().get('usage', {})}"
                )
                return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"HTTP error: {e.response.status_code} - {e.response.text} - {str(e)}",
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=502, detail="Failed to connect to API"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
