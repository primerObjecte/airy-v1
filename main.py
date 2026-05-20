import asyncio
import os
from dotenv import load_dotenv
from core.runtime import AiryRuntime

if __name__ == "__main__":
    load_dotenv()
    runtime = AiryRuntime()
    try:
        asyncio.run(runtime.start())
    except KeyboardInterrupt:
        try:
            asyncio.run(runtime.stop())
        except RuntimeError:
            pass
