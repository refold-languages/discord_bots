import { listTypes } from './constants';

const { blacklist, watchlist } = listTypes;

interface WordListInterface {
  text: string;
  listType: string;
  filterType: string;
}

export const wordList: WordListInterface[] = [
  // BLACKLIST //
  {
    text: 'nigger',
    listType: blacklist,
    filterType: 'includes'
  },
  {
    text: 'nignog',
    listType: blacklist,
    filterType: 'exact'
  },
  {
    text: 'niggaboo',
    listType: blacklist,
    filterType: 'exact'
  },
  {
    text: 'nigaboo',
    listType: blacklist,
    filterType: 'exact'
  },
  {
    text: 'nigga boo',
    listType: blacklist,
    filterType: 'exact'
  },
  {
    text: 'nigg',
    listType: blacklist,
    filterType: 'exact'
  },
  {
    text: 'niggers',
    listType: blacklist,
    filterType: 'exact'
  },
  {
    text: 'niglet',
    listType: blacklist,
    filterType: 'exact'
  },
  {
    text: 'paki',
    listType: blacklist,
    filterType: 'exact'
  },
  {
    text: 'pole smoker',
    listType: blacklist,
    filterType: 'exact'
  },
  {
    text: 'pollock',
    listType: blacklist,
    filterType: 'exact'
  },
  {
    text: 'porch monkey',
    listType: blacklist,
    filterType: 'exact'
  },
  {
    text: 'porchmonkey',
    listType: blacklist,
    filterType: 'exact'
  },
  {
    text: 'spik',
    listType: blacklist,
    filterType: 'exact'
  },
  {
    text: 'spic',
    listType: blacklist,
    filterType: 'exact'
  },
  {
    text: 'beaner',
    listType: blacklist,
    filterType: 'exact'
  },
  {
    text: 'sand nigga',
    listType: blacklist,
    filterType: 'exact'
  },
  {
    text: 'sand niger',
    listType: blacklist,
    filterType: 'exact'
  },
  {
    text: 'niga-boo',
    listType: blacklist,
    filterType: 'exact'
  },
  {
    text: 'bigaboo',
    listType: blacklist,
    filterType: 'exact'
  },
  {
    text: 'fag',
    listType: blacklist,
    filterType: 'exact'
  },
  {
    text: 'faggot',
    listType: blacklist,
    filterType: 'exact'
  },
  {
    text: 'fagget',
    listType: blacklist,
    filterType: 'exact'
  },
  {
    text: 'mcfagget',
    listType: blacklist,
    filterType: 'exact'
  },
  {
    text: 'mcfaggot',
    listType: blacklist,
    filterType: 'exact'
  },
  // WATCHLIST //
  {
    text: '9DeY3qZLNYI',
    listType: watchlist,
    filterType: 'includes'
  },
  {
    text: 'ztk54w8Bems',
    listType: watchlist,
    filterType: 'includes'
  },
  {
    text: 'rule 4',
    listType: watchlist,
    filterType: 'exact'
  },
  {
    text: 'rule4',
    listType: watchlist,
    filterType: 'exact'
  },
  {
    text: 'politics',
    listType: watchlist,
    filterType: 'exact'
  },
  {
    text: 'amendment',
    listType: watchlist,
    filterType: 'includes'
  },
  {
    text: 'niger',
    listType: watchlist,
    filterType: 'exact'
  },
  {
    text: 'nigget',
    listType: watchlist,
    filterType: 'includes'
  },
  {
    text: 'nig',
    listType: watchlist,
    filterType: 'exact'
  },
  {
    text: 'bible',
    listType: watchlist,
    filterType: 'exact'
  },
  {
    text: 'trump',
    listType: watchlist,
    filterType: 'exact'
  },
  {
    text: 'obama',
    listType: watchlist,
    filterType: 'exact'
  },
  {
    text: 'biden',
    listType: watchlist,
    filterType: 'exact'
  },
  {
    text: 'AOC',
    listType: watchlist,
    filterType: 'exact'
  },
  {
    text: 'border wall',
    listType: watchlist,
    filterType: 'exact'
  },
  {
    text: 'snowflake',
    listType: watchlist,
    filterType: 'includes'
  },
  {
    text: 'anti-vax',
    listType: watchlist,
    filterType: 'includes'
  },
  {
    text: 'anti vax',
    listType: watchlist,
    filterType: 'includes'
  },
  {
    text: 'kungflu',
    listType: watchlist,
    filterType: 'exact'
  },
  {
    text: 'kung-flu',
    listType: watchlist,
    filterType: 'exact'
  },
  {
    text: 'kung flu',
    listType: watchlist,
    filterType: 'exact'
  },
  {
    text: 'chinese virus',
    listType: watchlist,
    filterType: 'exact'
  },
  {
    text: 'china virus',
    listType: watchlist,
    filterType: 'exact'
  },
  {
    text: 'china-virus',
    listType: watchlist,
    filterType: 'exact'
  },
  {
    text: 'ben shapiro',
    listType: watchlist,
    filterType: 'exact'
  },
  {
    text: 'jordan peterson',
    listType: watchlist,
    filterType: 'exact'
  },
  {
    text: 'bernie sanders',
    listType: watchlist,
    filterType: 'exact'
  },
  {
    text: 'bernie',
    listType: watchlist,
    filterType: 'exact'
  },
  {
    text: 'alex jones',
    listType: watchlist,
    filterType: 'exact'
  },
  {
    text: 'nancy pelosi',
    listType: watchlist,
    filterType: 'exact'
  },
  {
    text: 'pelosi',
    listType: watchlist,
    filterType: 'includes'
  },
  {
    text: 'shapiro',
    listType: watchlist,
    filterType: 'includes'
  },
  {
    text: 'election',
    listType: watchlist,
    filterType: 'exact'
  },
  {
    text: 'ivermectin',
    listType: watchlist,
    filterType: 'exact'
  },
  {
    text: 'hydroxychloroquine',
    listType: watchlist,
    filterType: 'exact'
  },
  {
    text: 'johnson and johnson',
    listType: watchlist,
    filterType: 'exact'
  },
  {
    text: 'cnn',
    listType: watchlist,
    filterType: 'exact'
  },
  {
    text: 'msnbc',
    listType: watchlist,
    filterType: 'exact'
  },
  {
    text: 'fox',
    listType: watchlist,
    filterType: 'exact'
  }
];
