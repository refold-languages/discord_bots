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
Object.defineProperty(exports, "__esModule", { value: true });
exports.sendToJail = void 0;
const copyMessageToChannel_1 = require("../copyMessageToChannel");
const generateArchivePayload_1 = require("../generateArchivePayload");
const sendToJail = (message, jailChannel, matchedWord) => __awaiter(void 0, void 0, void 0, function* () {
    var _a, _b, _c, _d;
    const jailRole = (_a = message === null || message === void 0 ? void 0 : message.member) === null || _a === void 0 ? void 0 : _a.guild.roles.cache.find((role) => role.name === 'Jailed');
    const botHasArchiverPermissions = (_c = (_b = message === null || message === void 0 ? void 0 : message.guild) === null || _b === void 0 ? void 0 : _b.me) === null || _c === void 0 ? void 0 : _c.hasPermission('MANAGE_ROLES');
    if (!botHasArchiverPermissions) {
        console.error('Bot does not have sufficient permissions');
        return;
    }
    if (jailRole) {
        const currentUser = (_d = message === null || message === void 0 ? void 0 : message.guild) === null || _d === void 0 ? void 0 : _d.members.cache.get(message.author.id);
        const hasPatreonRole = currentUser === null || currentUser === void 0 ? void 0 : currentUser.roles.cache.find((role) => role.name === 'Refolder');
        const hasServerBoosterRole = currentUser === null || currentUser === void 0 ? void 0 : currentUser.roles.cache.find((role) => role.name === 'Server Booster');
        if (hasPatreonRole && hasServerBoosterRole) {
            yield (currentUser === null || currentUser === void 0 ? void 0 : currentUser.roles.set([
                hasServerBoosterRole,
                hasPatreonRole,
                jailRole
            ]));
        }
        else if (hasPatreonRole) {
            yield (currentUser === null || currentUser === void 0 ? void 0 : currentUser.roles.set([hasPatreonRole, jailRole]));
        }
        else if (hasServerBoosterRole) {
            yield (currentUser === null || currentUser === void 0 ? void 0 : currentUser.roles.set([hasServerBoosterRole, jailRole]));
        }
        else {
            yield (currentUser === null || currentUser === void 0 ? void 0 : currentUser.roles.set([jailRole]));
        }
        const archivePayload = generateArchivePayload_1.generateArchivePayload(message);
        return copyMessageToChannel_1.copyMessageToChannel(message, jailChannel, archivePayload, true, matchedWord);
    }
    console.log('Jail role not found');
});
exports.sendToJail = sendToJail;
//# sourceMappingURL=sendToJail.js.map