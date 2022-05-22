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
exports.copyMessageToChannel = void 0;
const discord_js_1 = __importDefault(require("discord.js"));
const copyMessageToChannel = (message, channel, archivePayload, provideMessageInfo, matchedWord) => __awaiter(void 0, void 0, void 0, function* () {
    const archiveEmbed = new discord_js_1.default.MessageEmbed()
        .setColor(archivePayload.archiveColor)
        .setTitle(archivePayload.archiveTitle)
        .setDescription(message)
        .setTimestamp()
        .setFooter(`Shared by: ${archivePayload.author.username}`, archivePayload.authorAvatar);
    if (archivePayload.attachments) {
        const hFileSize = function (bytes, si = false) {
            let u, b = bytes, t = si ? 1000 : 1024;
            ['', si ? 'k' : 'K', ...'MGTPEZY'].find((x) => ((u = x), (b /= t), Math.pow(b, 2) < 1));
            return `${u ? (t * b).toFixed(1) : bytes} ${u}${!si && u ? 'i' : ''}B`;
        };
        archivePayload.attachments.forEach((attachment) => {
            if (attachment.url.match(/.(jpg|jpeg|png|gif|bmp|ico)$/i)) {
                archiveEmbed.setImage(attachment.url);
            }
            else {
                const fileSize = hFileSize(attachment.size);
                archiveEmbed.addFields({
                    name: 'Attachment',
                    value: `[${attachment.name}](${attachment.url}) \`${fileSize}\``
                });
            }
        });
    }
    if (archivePayload.URLs) {
        archiveEmbed.setURL(archivePayload.URLs[0]);
    }
    archiveEmbed.addFields({
        name: '\u200B',
        value: `[Original Post](${archivePayload.authorURL})`
    });
    if (matchedWord) {
        archiveEmbed.addFields({
            name: 'Flagged Word',
            value: matchedWord
        });
    }
    if (provideMessageInfo) {
        archiveEmbed.addFields({
            name: 'Flagged User ID',
            value: archivePayload.author.id,
            inline: true
        }, {
            name: 'Flagged Message ID',
            value: message.id,
            inline: true
        });
    }
    yield channel.send(archiveEmbed);
    if (archivePayload.URLs) {
        const numURLs = archivePayload.URLs.length;
        archivePayload.URLs.forEach((URL, index) => {
            channel.send(`\`[URL ${index + 1}/${numURLs}]\` ${URL}`);
        });
    }
});
exports.copyMessageToChannel = copyMessageToChannel;
//# sourceMappingURL=copyMessageToChannel.js.map