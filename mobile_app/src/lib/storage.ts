const KEY = "people-store-v1";

export function save<T>(data: T) {
  localStorage.setItem(KEY, JSON.stringify(data));
}

export function load<T>(): T | null {
  const raw = localStorage.getItem(KEY);
  return raw ? (JSON.parse(raw) as T) : null;
}
