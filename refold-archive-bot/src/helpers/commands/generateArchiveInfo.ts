export const generateArchiveColor = (): string => {
  const archiveColor: string = '#000000'.replace(/0/g, () => {
    return (~~(Math.random() * 16)).toString(16);
  }); // see: https://stackoverflow.com/a/5092872
  return archiveColor;
};

export const generateArchiveTitle = (cleanedContent: string): string => {
  let abbreviatedTitle: string = 'Share'; // default

  // split the content by newlines to derive a title
  const separators: RegExp = new RegExp('[\n]');
  if (cleanedContent.split(separators)) {
    abbreviatedTitle = cleanedContent.split(separators)[0];
  }

  // remove any double space left by removing prefix + command
  abbreviatedTitle = abbreviatedTitle.replace('  ', ' ');

  // abbreviate title to less <=60 characters
  const titleLength: number = 60;
  if (abbreviatedTitle.length >= titleLength) {
    abbreviatedTitle = abbreviatedTitle.substring(0, titleLength - 3) + '...';
  }
  return abbreviatedTitle;
};
