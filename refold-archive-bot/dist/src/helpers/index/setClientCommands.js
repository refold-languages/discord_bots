"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.setClientCommands = void 0;
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const dev = process.env.NODE_ENV === 'dev';
const getCommandFiles = () => {
    const commandFiles = fs_1.default
        .readdirSync(path_1.default.join(__dirname, '../../../src/commands'))
        .filter((file) => file.endsWith(`${dev ? '.ts' : '.js'}`));
    return commandFiles;
};
const setClientCommands = (client) => {
    var _a;
    const commandFiles = getCommandFiles();
    for (const file of commandFiles) {
        const command = require(`../../../src/commands/${file}`);
        (_a = client.commands) === null || _a === void 0 ? void 0 : _a.set(command.name, command);
    }
};
exports.setClientCommands = setClientCommands;
//# sourceMappingURL=setClientCommands.js.map