export const ADMIN_TOKEN_COOKIE = 'auxilia_admin_token';

export function hasAdminToken(token?: string | null) {
  return Boolean(token && token.trim().length > 0);
}
