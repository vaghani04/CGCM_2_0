import httpx
from fastapi import Depends, HTTPException, status
from src.app.config.settings import settings


class EmbeddingService:
    def __init__(self):

        self.voyageai_api_key = settings.VOYAGEAI_API_KEY
        self.JINA_EMBED_SUFFIX = "embeddings"
        self.voyageai_base_url = settings.VOYAGEAI_BASE_URL
        self.EMBED_SUFFIX = "embed"
        self.timeout = httpx.Timeout(
            connect=60.0,  # Time to establish a connection
            read=300.0,  # Time to read the response
            write=300.0,  # Time to send data
            pool=60.0,  # Time to wait for a connection from the pool
        )

    async def voyageai_dense_embeddings(
        self,
        model_name: str,
        dimension: int,
        inputs: list,
        input_type: str = "document",
    ):
        url = f"{self.voyageai_base_url}/{self.JINA_EMBED_SUFFIX}"

        headers = {
            "Authorization": f"Bearer {self.voyageai_api_key}",
            "Content-Type": "application/json",
        }

        data = {
            "input": inputs,
            "model": model_name,
            "input_type": input_type,
            "output_dimension": dimension,
        }

        try:

            async with httpx.AsyncClient(
                verify=False, timeout=self.timeout
            ) as client:
                response = await client.post(url, headers=headers, json=data)
                response.raise_for_status()
                response = response.json()
                embedding_list = [
                    item["embedding"] for item in response["data"]
                ]
                return embedding_list

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"HTTP error occurred in httpx status error  : {str(e)} - {e.response.text}",
            )

        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"HTTP error in httpx voyage dense embed: {str(e)}",
            )

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unknown Exception occurred in voyageai_dense_embedding: {str(e)}",
            )
