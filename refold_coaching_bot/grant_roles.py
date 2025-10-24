#!/usr/bin/env python3
"""
Script to grant roles to existing users who completed onboarding but don't have roles yet.
This fixes the issue where users completed onboarding before the role ID was properly configured.
"""

import asyncio
import discord
from discord.ext import commands
from config import config
from data_manager import data_manager

class RoleGrantBot(commands.Bot):
    """Simple bot to grant roles to existing users."""
    
    def __init__(self):
        intents = discord.Intents.all()
        intents.members = True
        super().__init__(intents=intents, command_prefix='!')
    
    async def on_ready(self):
        """Called when bot is ready."""
        print(f'Role Grant Bot logged in as {self.user}')
        print(f'Bot ID: {self.user.id}')
        print(f'Guilds: {len(self.guilds)}')
        print(f'Intensive Role ID: {config.INTENSIVE_ROLE_ID}')
        
        if not config.INTENSIVE_ROLE_ID:
            print("❌ INTENSIVE_ROLE_ID not configured!")
            await self.close()
            return
        
        # Get all users
        users = data_manager.get_all_users()
        print(f"Found {len(users)} users in database")
        
        # Find users without roles
        users_without_roles = []
        for discord_id_str, user_data in users.items():
            if not user_data.get('role_granted', False):
                users_without_roles.append((int(discord_id_str), user_data))
        
        print(f"Found {len(users_without_roles)} users without roles")
        
        if not users_without_roles:
            print("✅ All users already have roles!")
            await self.close()
            return
        
        # Check all guilds for the role
        role = None
        correct_guild = None
        
        for guild in self.guilds:
            print(f"Checking guild: {guild.name} (ID: {guild.id})")
            found_role = guild.get_role(config.INTENSIVE_ROLE_ID)
            if found_role:
                role = found_role
                correct_guild = guild
                print(f"✅ Found role '{role.name}' in guild '{guild.name}'")
                break
        
        if not role:
            print(f"\n❌ Role with ID {config.INTENSIVE_ROLE_ID} not found in any guild!")
            print("Available guilds:")
            for guild in self.guilds:
                print(f"  - {guild.name} (ID: {guild.id})")
            await self.close()
            return
        
        print(f"✅ Found role: {role.name}")
        
        success_count = 0
        for discord_id, user_data in users_without_roles:
            try:
                member = correct_guild.get_member(discord_id)
                if member:
                    await member.add_roles(role)
                    user_data['role_granted'] = True
                    data_manager.save_user(discord_id, user_data)
                    print(f"✅ Granted role to {member.display_name} ({discord_id})")
                    success_count += 1
                else:
                    print(f"❌ Member {discord_id} not found in guild '{correct_guild.name}'")
            except Exception as e:
                print(f"❌ Error granting role to {discord_id}: {e}")
        
        print(f"✅ Successfully granted roles to {success_count} users")
        await self.close()

async def main():
    """Main function."""
    bot = RoleGrantBot()
    try:
        await bot.start(config.BOT_TOKEN)
    except KeyboardInterrupt:
        print("Bot shutdown requested...")
    except Exception as e:
        print(f"Bot crashed: {e}")
    finally:
        if not bot.is_closed():
            await bot.close()

if __name__ == "__main__":
    asyncio.run(main())
