"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.determineIsExcludeChannel = void 0;
const config_json_1 = __importDefault(require("../../config.json"));
const determineIsExcludeChannel = (command, message, isEmojiCommand = false) => {
    const currentChannel = message.channel;
    const formattedChannelName = currentChannel.name && currentChannel.name.toLowerCase();
    let isExcludedChannel;
    if (isEmojiCommand) {
        isExcludedChannel =
            config_json_1.default.emojiCommands[command].excludedChannels.includes(formattedChannelName);
        if (isExcludedChannel)
            return true;
        return false;
    }
    isExcludedChannel =
        config_json_1.default[command].excludedChannels.includes(formattedChannelName);
    if (isExcludedChannel)
        return true;
    return false;
};
exports.determineIsExcludeChannel = determineIsExcludeChannel;
//# sourceMappingURL=determineIsExcludedChannel.js.map