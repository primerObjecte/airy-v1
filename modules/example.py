"""
Example module for Airy userbot
Demonstrates how to create a basic module with commands
"""

from core.context import CommandContext
from core.events import Event


class ExampleModule:
    """Example module showing basic command handling"""

    def __init__(self, runtime):
        self.runtime = runtime
        self.name = "example"
        # Subscribe to command events
        self.runtime.event_bus.on("command", self.handle_command, module_name=self.name)

    async def handle_command(self, event: Event):
        """Handle commands dispatched by the runtime"""
        data = event.data
        command = data.get("command", "").lower()
        args = data.get("args", "").strip()

        # Simple ping command
        if command == "ping":
            await data["event"].reply("🏓 Pong!")

        # Echo command
        elif command == "echo":
            if args:
                await data["event"].reply(f"Echo: {args}")
            else:
                await data["event"].reply("Usage: .echo <text>")

        # Help command
        elif command == "help":
            help_text = """
📚 **Airy Userbot Commands:**

`.ping` - Check if bot is alive
`.echo <text>` - Echo text back
`.help` - Show this message
            """
            await data["event"].reply(help_text)

    async def stop(self):
        """Called when module is unloaded"""
        pass


# Export module instance
module = ExampleModule(None)


async def initialize_module(runtime):
    """Called by ModuleLoader to initialize the module"""
    global module
    module.runtime = runtime
    # Re-subscribe after initialization
    runtime.event_bus.on("command", module.handle_command, module_name=module.name)
