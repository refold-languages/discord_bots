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
exports.setupOnGuildMemberAdd = void 0;
const config_json_1 = __importDefault(require("../config.json"));
const userIdBanList = new Set(config_json_1.default.banList);
const setupOnGuildMemberAdd = (client) => __awaiter(void 0, void 0, void 0, function* () {
    return client.on('guildMemberAdd', (member) => __awaiter(void 0, void 0, void 0, function* () {
        const membersModLogChannel = yield client.channels.fetch(process.env.MEMBERS_MOD_LOG_CHANNEL_ID || config_json_1.default.membersModLogChannelId);
        if (member.user.bot)
            return;
        const userHasBannableId = userIdBanList.has(member.id);
        if (userHasBannableId && membersModLogChannel.isText()) {
            yield member.send('We have a moderator network that reports known trolls and troublemakers. You were reported in another server and so we preemptively removed you from Refold.');
            yield member.ban().catch((error) => console.error(error));
            return membersModLogChannel.send(`${member.user} was automatically banned from the auto ban watch-list`);
        }
        return;
    }));
});
exports.setupOnGuildMemberAdd = setupOnGuildMemberAdd;
//# sourceMappingURL=setupOnGuildMemberAdd.js.map