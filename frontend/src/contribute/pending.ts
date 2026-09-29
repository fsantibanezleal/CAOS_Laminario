// The files chosen for a case's images, by image id, for the life of the page: they survive the move from
// /contribute/new to the case's own address once it is stored, and are gone after a reload (a browser does not keep a
// chosen file), when the case asks for them again.
const files = new Map<string, File>();

export const pending = {
  get: (token: string): File | undefined => files.get(token),
  set: (token: string, file: File): void => {
    files.set(token, file);
  },
  delete: (token: string): void => {
    files.delete(token);
  },
  has: (token: string): boolean => files.has(token),
};
