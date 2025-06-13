from fastapi import Depends
from src.app.usecases.user_query_usecases.user_query_helper import UserQueryHelper
from typing import Dict, Any
class UserQueryUseCase:
    def __init__(self,
                user_query_helper: UserQueryHelper = Depends(UserQueryHelper)):
        self.user_query_helper = user_query_helper

    async def execute(self, user_query: Dict[str, Any]):
        import asyncio
        import time
        
        start_time = time.time()
        
        # Execute all 4 context gathering tasks in parallel
        print("🚀 Starting parallel context gathering from 4 sources...")
        
        # Create tasks for parallel execution
        repo_map_task = asyncio.create_task(
            self.user_query_helper.context_from_repo_map(user_query),
            name="repo_map_context"
        )
        
        rag_task = asyncio.create_task(
            self.user_query_helper.context_from_rag(user_query),
            name="rag_context"
        )
        
        nl_task = asyncio.create_task(
            self.user_query_helper.context_from_nl_insights(user_query),
            name="nl_context"
        )
        
        grep_task = asyncio.create_task(
            self.user_query_helper.context_from_grep_search(user_query),
            name="grep_search_context"
        )
        
        # Wait for all tasks to complete in parallel
        try:
            repo_map_context, rag_context, nl_context, grep_search_context = await asyncio.gather(
                repo_map_task,
                rag_task,
                nl_task,
                grep_task,
                return_exceptions=True
            )
            
            print("✓ All parallel context gathering completed")
            
            # Handle exceptions for individual tasks
            if isinstance(repo_map_context, Exception):
                print(f"❌ Repo map context failed: {repo_map_context}")
                repo_map_context = []
                
            if isinstance(rag_context, Exception):
                print(f"❌ RAG context failed: {rag_context}")
                rag_context = []
                
            if isinstance(nl_context, Exception):
                print(f"❌ NL context failed: {nl_context}")
                nl_context = []
                
            if isinstance(grep_search_context, Exception):
                print(f"❌ Grep search context failed: {grep_search_context}")
                grep_search_context = []
            
            # Build final response with conditional logic
            final_response = {}
            
            # Always include NL context
            final_response["nl_context"] = nl_context
            print(f"✓ NL context: {len(nl_context) if isinstance(nl_context, list) else 'included'}")
            
            # Always include repo_map_context and rag_context if they have data
            final_response["repo_map_context"] = repo_map_context
            final_response["rag_context"] = rag_context
            
            # Check if both rag_context and repo_map_context are empty
            rag_empty = not rag_context or (isinstance(rag_context, list) and len(rag_context) == 0)
            repo_map_empty = not repo_map_context or (isinstance(repo_map_context, list) and len(repo_map_context) == 0)
            
            # Only include grep_search_context if both rag and repo_map are empty
            if rag_empty and repo_map_empty:
                final_response["grep_search_context"] = grep_search_context
                print(f"✓ Grep search context included (RAG and repo_map empty): {len(grep_search_context) if isinstance(grep_search_context, list) else 'included'}")
            else:
                print("ℹ️ Grep search context excluded (RAG or repo_map have data)")
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            print(f"🎯 Total parallel context gathering time: {processing_time:.2f} seconds")
            print(f"📊 Final response contains: {list(final_response.keys())}")
            
            return final_response
            
        except Exception as e:
            print(f"❌ Error during parallel context gathering: {e}")
            end_time = time.time()
            processing_time = end_time - start_time
            print(f"⏱️ Processing time before error: {processing_time:.2f} seconds")
            raise e