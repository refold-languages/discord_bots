"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const discord_js_1 = __importDefault(require("discord.js"));
require("dotenv/config");
const config_json_1 = __importDefault(require("../config.json"));
const setClientCommands_1 = require("./helpers/index/setClientCommands");
const setupMessageReactionAdd_1 = require("./setupMessageReactionAdd");
const setupOnGuildMemberAdd_1 = require("./setupOnGuildMemberAdd");
const setupOnMessage_1 = require("./setupOnMessage");
let client = new discord_js_1.default.Client();
client.commands = new discord_js_1.default.Collection();
(() => __awaiter(void 0, void 0, void 0, function* () {
    const token = process.env.TOKEN || config_json_1.default.token;
    yield client.login(token).catch((error) => {
        console.error(error);
        process.exit(0);
    });
    console.info('Bot logged in using token');
    setClientCommands_1.setClientCommands(client);
    client.once('ready', () => {
        console.info('Bot is ready!');
    });
    yield setupOnGuildMemberAdd_1.setupOnGuildMemberAdd(client);
    yield setupMessageReactionAdd_1.setupOnMessageReactionAdd(client);
    yield setupOnMessage_1.setupOnMessage(client);
}))();
//# sourceMappingURL=index.js.map