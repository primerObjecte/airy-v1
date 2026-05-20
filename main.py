import asyncio
from core.runtime import AiryRuntime

if __name__ == "__main__":
    runtime = AiryRuntime()
    try:
        asyncio.run(runtime.start())
    except KeyboardInterrupt:
        try:
            asyncio.run(runtime.stop())
        except RuntimeError:
            pass
