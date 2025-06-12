class ExtractNLContextUseCase:
    def __init__(self):
        pass

    async def execute(self, codebase_path: str):
        context = "This is a test context"
        return context