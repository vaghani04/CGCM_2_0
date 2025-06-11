import httpx
import time
from fastapi import Depends, HTTPException, status
from src.app.config.settings import settings
from src.app.utils.logging_util import loggers

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
            start_time = time.time()
            
            # Calculate approximate input tokens (rough estimate)
            total_input_chars = sum(len(str(item)) for item in inputs)
            approx_input_tokens = total_input_chars // 4  # Very rough estimation
            
            async with httpx.AsyncClient(
                verify=False, timeout=self.timeout
            ) as client:
                response = await client.post(url, headers=headers, json=data)
                response.raise_for_status()
                response_json = response.json()
                embedding_list = [
                    item["embedding"] for item in response_json["data"]
                ]
                
                end_time = time.time()
                duration = end_time - start_time
                
                # Get usage information if available
                usage_info = response_json.get("usage", {})
                prompt_tokens = usage_info.get("prompt_tokens", approx_input_tokens)
                total_tokens = usage_info.get("total_tokens", None)
                
                # Comprehensive usage log
                loggers["voyageai"].info(
                    f"VOYAGEAI_API_USAGE | "
                    f"INPUTS: {len(inputs)} | "
                    f"INPUT_TOKENS: {prompt_tokens} | "
                    f"OUTPUT_EMBEDDINGS: {len(embedding_list)} | "
                    f"TOTAL_TOKENS: {total_tokens} | "
                    f"DURATION_SEC: {duration:.2f} | "
                    f"STATUS: {response.status_code}"
                )
                
                return embedding_list

        except httpx.HTTPStatusError as e:
            loggers["voyageai"].error(
                f"VOYAGEAI_API_USAGE | "
                f"STATUS: ERROR | "
                f"ERROR_CODE: {e.response.status_code} | "
                f"ERROR_DETAIL: {str(e)} - {e.response.text}"
            )
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"HTTP error occurred in httpx status error  : {str(e)} - {e.response.text}",
            )

        except httpx.HTTPError as e:
            loggers["voyageai"].error(
                f"VOYAGEAI_API_USAGE | "
                f"STATUS: ERROR | "
                f"ERROR_DETAIL: {str(e)}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"HTTP error in httpx voyage dense embed: {str(e)}",
            )

        except Exception as e:
            loggers["voyageai"].error(
                f"VOYAGEAI_API_USAGE | "
                f"API_KEY: {self.voyageai_api_key} | "
                f"MODEL: {model_name} | "
                f"STATUS: ERROR | "
                f"ERROR_DETAIL: {str(e)}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unknown Exception occurred in voyageai_dense_embedding: {str(e)}",
            )
