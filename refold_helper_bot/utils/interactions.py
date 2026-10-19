"""
Slash-command helpers for Refold Helper Bot.

Interactions can only be answered once through ``interaction.response``; every
later message (or any message after a ``defer()``) has to go through the
followup webhook. ``respond`` hides that distinction so command bodies can
reply the same way regardless of how far along the interaction is.
"""

from typing import Optional

import discord


async def respond(interaction: discord.Interaction, content: Optional[str] = None,
                  *, ephemeral: bool = False, **kwargs) -> None:
    """Reply to an interaction, using the followup webhook once it has been answered."""
    if interaction.response.is_done():
        await interaction.followup.send(content, ephemeral=ephemeral, **kwargs)
    else:
        await interaction.response.send_message(content, ephemeral=ephemeral, **kwargs)


class ConfirmView(discord.ui.View):
    """Confirm / Cancel buttons that only the invoking user can press.

    Replaces the old ``wait_for('reaction_add')`` and typed-"CONFIRM" prompts.
    After ``await view.wait()``, ``view.confirmed`` is True, False, or None
    (timed out).
    """

    def __init__(self, user_id: int, *, timeout: float = 60.0,
                 confirm_label: str = 'Confirm', danger: bool = True):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.confirmed: Optional[bool] = None
        self.confirm_button.label = confirm_label
        if not danger:
            self.confirm_button.style = discord.ButtonStyle.success

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Only the person who ran this command can answer.", ephemeral=True)
            return False
        return True

    async def _finish(self, interaction: discord.Interaction, confirmed: bool) -> None:
        self.confirmed = confirmed
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._finish(interaction, True)

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._finish(interaction, False)


async def confirm(interaction: discord.Interaction, prompt: str, *,
                  timeout: float = 60.0, confirm_label: str = 'Confirm',
                  ephemeral: bool = True, embed: Optional[discord.Embed] = None) -> bool:
    """Ask the invoking user to confirm; returns True only on an explicit Confirm."""
    view = ConfirmView(interaction.user.id, timeout=timeout, confirm_label=confirm_label)
    await respond(interaction, prompt, ephemeral=ephemeral, view=view,
                  **({'embed': embed} if embed else {}))
    await view.wait()
    if view.confirmed is None:
        await respond(interaction, "⏰ Timed out - nothing was changed.", ephemeral=ephemeral)
    elif not view.confirmed:
        await respond(interaction, "❌ Cancelled - nothing was changed.", ephemeral=ephemeral)
    return bool(view.confirmed)


async def read_text_attachment(attachment: discord.Attachment, *,
                               max_bytes: int = 1_000_000) -> str:
    """Download a small text attachment (CSV etc.) and decode it as UTF-8.

    Raises ValueError for oversized or undecodable files so callers can report
    a clear message instead of a generic failure.
    """
    if attachment.size > max_bytes:
        raise ValueError(f"File is too large ({attachment.size:,} bytes; max {max_bytes:,}).")
    data = await attachment.read()
    try:
        # utf-8-sig strips the BOM that spreadsheet exports often add.
        return data.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise ValueError("File is not valid UTF-8 text. Export it as CSV (UTF-8) and try again.")
