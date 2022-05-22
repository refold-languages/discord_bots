export interface ListTypesInterface {
  watchlist: string;
  greylist: string;
  blacklist: string;
}

export const listTypes: ListTypesInterface = {
  watchlist: 'WATCH_LIST',
  greylist: 'GREY_LIST',
  blacklist: 'BLACK_LIST'
};
