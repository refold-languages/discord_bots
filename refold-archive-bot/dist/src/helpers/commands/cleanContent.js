"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.cleanContent = exports.getCommandList = void 0;
const getCommandList = (aliases, name) => {
    let commandList = Array.from(aliases);
    commandList.unshift(name);
    return commandList;
};
exports.getCommandList = getCommandList;
const cleanContent = (commandList, messageContent, prefix) => {
    let cleanedMessage = '';
    for (let command of commandList) {
        cleanedMessage = messageContent.replace(prefix + command, '');
    }
    return cleanedMessage;
};
exports.cleanContent = cleanContent;
//# sourceMappingURL=cleanContent.js.map