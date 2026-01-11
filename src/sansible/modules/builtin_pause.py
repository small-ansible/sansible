"""
Sansible pause module

Pause playbook execution.
"""

import asyncio

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class PauseModule(Module):
    """
    Pause playbook execution for a given time or until input.
    
    Note: In non-interactive mode, prompt pauses will be skipped.
    """
    
    name = "pause"
    required_args = []
    optional_args = {
        "seconds": None,        # Number of seconds to pause
        "minutes": None,        # Number of minutes to pause
        "prompt": None,         # Message to display (prompt for input - limited support)
        "echo": True,           # Echo user input (for prompts)
    }
    
    async def run(self) -> ModuleResult:
        """Pause execution."""
        seconds = self.get_arg("seconds")
        minutes = self.get_arg("minutes")
        prompt = self.get_arg("prompt")
        
        # Calculate total pause time
        pause_time = 0
        if seconds is not None:
            pause_time += int(seconds)
        if minutes is not None:
            pause_time += int(minutes) * 60
        
        # Check mode - just report what would happen
        if self.check_mode:
            if pause_time > 0:
                return ModuleResult(
                    changed=False,
                    msg=f"Would pause for {pause_time} seconds",
                )
            elif prompt:
                return ModuleResult(
                    changed=False,
                    msg=f"Would pause for prompt: {prompt}",
                )
            else:
                return ModuleResult(
                    changed=False,
                    msg="Would pause indefinitely (press Ctrl+C to continue)",
                )
        
        # If we have a pause time, sleep
        if pause_time > 0:
            await asyncio.sleep(pause_time)
            return ModuleResult(
                changed=False,
                msg=f"Paused for {pause_time} seconds",
                results={
                    "delta": pause_time,
                    "seconds": pause_time,
                },
            )
        
        # If prompt but no pause time, in automation mode we just log and continue
        # Full interactive prompt support would require terminal handling
        if prompt:
            # In non-interactive mode, just continue
            return ModuleResult(
                changed=False,
                msg=f"Prompt (skipped in non-interactive mode): {prompt}",
                results={
                    "user_input": "",
                },
            )
        
        # No time and no prompt - would be indefinite pause
        # In automation, we skip this
        return ModuleResult(
            changed=False,
            msg="Pause without duration or prompt (skipped)",
        )
