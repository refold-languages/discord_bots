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
exports.run = exports.description = exports.cooldown = exports.emojis = exports.aliases = exports.name = void 0;
const config_json_1 = __importDefault(require("../../config.json"));
const determineIsExcludedChannel_1 = require("../helpers/determineIsExcludedChannel");
const sendToArchiveChannel_1 = require("./../helpers/commands/sendToArchiveChannel");
exports.name = 'archive';
exports.aliases = ['share', 'save', 's'];
exports.emojis = ['📎', '🪱'];
exports.cooldown = 10;
exports.description = 'Clones a message and makes a custom embed in another channel';
const run = (client, message) => __awaiter(void 0, void 0, void 0, function* () {
    const hasExcludedChannels = config_json_1.default.archiveCommand.excludedChannels.length >= 1;
    if (hasExcludedChannels) {
        const isExcludedChannel = determineIsExcludedChannel_1.determineIsExcludeChannel('archiveCommand', message);
        if (isExcludedChannel)
            return;
    }
    yield sendToArchiveChannel_1.sendToArchiveChannel(client, message, 'command', exports.aliases);
});
exports.run = run;
//# sourceMappingURL=archive.js.map