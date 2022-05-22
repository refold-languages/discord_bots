"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.setupCooldown = void 0;
const discord_js_1 = __importDefault(require("discord.js"));
const cooldowns = new discord_js_1.default.Collection();
const config = require('../../../config.json');
const prefix = config.command.prefix;
const setupCooldown = (client, command, message) => {
    const hasCoolDown = cooldowns.has(command.name);
    if (!hasCoolDown) {
        cooldowns.set(command.name, new discord_js_1.default.Collection());
    }
    const now = Date.now();
    const timestamps = cooldowns.get(command.name);
    const threeSeconds = 3;
    const cooldownAmount = (command.cooldown || threeSeconds) * 1000;
    const cooldownHasAuthor = timestamps.has(message.author.id);
    if (cooldownHasAuthor) {
        const expirationTime = timestamps.get(message.author.id) + cooldownAmount;
        if (now < expirationTime) {
            const timeLeft = (expirationTime - now) / 1000;
            return message.reply(`\`[COOLDOWN]\` Please wait ${timeLeft.toFixed(1)} second(s) before trying \`${prefix}${command.name}\` again.`);
        }
    }
    timestamps.set(message.author.id, now);
    setTimeout(() => timestamps.delete(message.author.id), cooldownAmount);
    try {
        return command.run(client, message);
    }
    catch (error) {
        console.log('[ERROR] Unable to execute command: ', command);
        console.error(error);
    }
};
exports.setupCooldown = setupCooldown;
//# sourceMappingURL=setupCooldown.js.map