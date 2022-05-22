"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.generateArchiveTitle = exports.generateArchiveColor = void 0;
const generateArchiveColor = () => {
    const archiveColor = '#000000'.replace(/0/g, () => {
        return (~~(Math.random() * 16)).toString(16);
    });
    return archiveColor;
};
exports.generateArchiveColor = generateArchiveColor;
const generateArchiveTitle = (cleanedContent) => {
    let abbreviatedTitle = 'Share';
    const separators = new RegExp('[\n]');
    if (cleanedContent.split(separators)) {
        abbreviatedTitle = cleanedContent.split(separators)[0];
    }
    abbreviatedTitle = abbreviatedTitle.replace('  ', ' ');
    const titleLength = 60;
    if (abbreviatedTitle.length >= titleLength) {
        abbreviatedTitle = abbreviatedTitle.substring(0, titleLength - 3) + '...';
    }
    return abbreviatedTitle;
};
exports.generateArchiveTitle = generateArchiveTitle;
//# sourceMappingURL=generateArchiveInfo.js.map